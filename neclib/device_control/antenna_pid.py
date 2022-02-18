r"""PID controller for telescope main dish.

Optimum control parameter is calculated using a simple function consists of
Proportional, Integral and Derivative terms:

.. math::

    u(t) = K_\mathrm{p} \, e(t)
    + K_\mathrm{i} \int e(\tau) \, \mathrm{d}\tau
    + K_\mathrm{d} \frac{ \mathrm{d}e(t) }{ \mathrm{d}t }

where :math:`K_\mathrm{p}, K_\mathrm{i}` and :math:`K_\mathrm{d}` are free parameters,
:math:`u(t)` is the parameter to control, and :math:`e(t)` is the error between command
value and actual value of reference parameter.

.. note::

    This script will be executed in high frequency with no vectorization, and there are
    many arrays updated frequently. These mean that the use of Numpy may not be the best
    choice to speed up the calculation. Measure the execution time first, then
    implement.

"""

__all__ = ["PIDController", "optimum_angle"]

import time
from typing import ClassVar, Dict, Tuple

import numpy as np

from .. import utils
from ..typing import AngleUnit, Literal


# Indices for 2-lists (mutable version of so-called 2-tuple).
Last = -2
Now = -1
# Default value for 2-lists.
DefaultTwoList = [np.nan, np.nan]


# Default values for PIDController.
DefaultK_p = 1.0
DefaultK_i = 0.5
DefaultK_d = 0.3
DefaultMaxSpeed = "2 deg/s"
DefaultMaxAcceleration = "2 deg/s^2"
DefaultErrorIntegCount = 50
DefaultThreshold = {
    "cmd_coord_change": "100 arcsec",
    "accel_limit_off": "20 arcsec",
    "target_accel_ignore": "2 deg/s^2",
}
ThresholdKeys = Literal["cmd_coord_change", "accel_limit_off", "target_accel_ignore"]


class PIDController:
    """PID controller for telescope antenna.

    PID controller, a classical but sophisticated controller for system which has some
    delay on response to some input. This controller handles only 1 device, so use 2
    instances for AzEl control of telescope antenna.

    Parameters
    ----------
    pid_param
        Free parameters for PID control, list of [K_p, K_i, K_d].
    max_speed
        Maximum speed for telescope motion.
    max_acceleration
        Maximum acceleration for telescope motion.
    error_integ_count
        Number of error data to be stored for integral term calculation.
    threshold
        Thresholds for conditional executions.

    Notes
    -----
    This controller adds constant term to the general PID formulation. This is an
    attempt to follow constant motions such as raster scanning and sidereal motion
    tracking.

    .. warning::

        When you are to assign ``ANGLE_UNIT`` other than its default value, ``deg``, you
        should fix the values of ``MAX_SPEED``, ``MAX_ACCELERATION``, and ``THRESHOLD``.

    This class keeps last 50 error values (by default) for integral term. This causes
    optimal PID parameters to change according to PID calculation frequency, as the time
    interval of the integration depends on the frequency.

    Examples
    --------
    >>> controller = PIDController(pid_param=[1.5, 0, 0])
    >>> speed = controller.get_speed(target_coordinate, encoder_reading)

    """

    ANGLE_UNIT: ClassVar[AngleUnit] = "deg"
    """Unit in which all public functions accept as its argument and return."""

    def __init__(
        self,
        *,
        pid_param: Tuple[float, float, float] = [DefaultK_p, DefaultK_i, DefaultK_d],
        max_speed: str = DefaultMaxSpeed,
        max_acceleration: str = DefaultMaxAcceleration,
        error_integ_count: int = DefaultErrorIntegCount,
        threshold: Dict[ThresholdKeys, str] = DefaultThreshold,
    ) -> None:
        self.k_p, self.k_i, self.k_d = pid_param
        self.max_speed = utils.parse_quantity_once(
            max_speed, unit=self.ANGLE_UNIT
        ).value
        self.max_acceleration = utils.parse_quantity_once(
            max_acceleration, unit=self.ANGLE_UNIT
        ).value
        self.error_integ_count = error_integ_count
        _threshold = DefaultThreshold.copy()
        _threshold.update(threshold)
        self.threshold = {
            k: utils.parse_quantity_once(v, unit=self.ANGLE_UNIT)
            for k, v in _threshold.items()
        }.value

        # Initialize parameter buffers.
        self._initialize()

    @property
    def dt(self) -> float:
        """Time interval of last 2 PID calculations."""
        return self.time[Now] - self.time[Last]

    @property
    def error_integral(self) -> float:
        """Integral of error."""
        _time, _error = np.array(self.time), np.array(self.error)
        dt = _time[1:] - _time[:-1]
        error_interpolated = (_error[1:] + _error[:-1]) / 2
        return np.nansum(error_interpolated * dt)

    @property
    def error_derivative(self) -> float:
        """Derivative of error."""
        return (self.error[Now] - self.error[Last]) / self.dt

    def _set_initial_parameters(self, cmd_coord: float, enc_coord: float) -> None:
        self._initialize()

        if np.isnan(self.cmd_speed[Now]):
            utils.update_list(self.cmd_speed, 0)
        utils.update_list(self.time, time.time())
        utils.update_list(self.cmd_coord, cmd_coord)
        utils.update_list(self.enc_coord, enc_coord)
        utils.update_list(self.error, cmd_coord - enc_coord)
        utils.update_list(self.target_speed, 0)

    def _initialize(self) -> None:
        if not hasattr(self, "cmd_speed"):
            self.cmd_speed = DefaultTwoList.copy()
        self.time = DefaultTwoList.copy() * int(self.error_integ_count / 2)
        self.cmd_coord = DefaultTwoList.copy()
        self.enc_coord = DefaultTwoList.copy()
        self.error = DefaultTwoList.copy() * int(self.error_integ_count / 2)
        self.target_speed = DefaultTwoList.copy()
        # Without `copy()`, updating one of them updates all its shared (not copied)
        # objects.

    def get_speed(
        self,
        cmd_coord: float,
        enc_coord: float,
        stop: bool = False,
    ) -> float:
        """Calculate valid drive speed.

        Parameters
        ----------
        cmd_coord
            Instructed Az/El coordinate.
        enc_coord
            Az/El encoder reading.
        stop
            If ``True``, the telescope won't move regardless of the inputs.

        Returns
        -------
        float
            Speed which will be commanded to motor, in original unit.

        """
        delta_cmd_coord = cmd_coord - self.cmd_coord[Now]
        if np.isnan(self.time[Now]) or (
            abs(delta_cmd_coord) > self.threshold["cmd_coord_change"]
        ):
            self._set_initial_parameters(cmd_coord, enc_coord)
            # Set default values on initial run or on detection of sudden jump of error,
            # which may indicate a change of command coordinate.
            # This will give too small `self.dt` later, but that won't propose any
            # problem, since `current_speed` goes to 0, and too large target_speed will
            # be ignored in `_calc_pid`.

        current_speed = self.cmd_speed[Now]
        # Encoder readings cannot be used, due to the lack of stability.

        utils.update_list(self.time, time.time())
        utils.update_list(self.cmd_coord, cmd_coord)
        utils.update_list(self.enc_coord, enc_coord)
        utils.update_list(self.error, cmd_coord - enc_coord)
        utils.update_list(
            self.target_speed, (cmd_coord - self.cmd_coord[Now]) / self.dt
        )

        # Calculate and validate drive speed.
        speed = self._calc_pid()
        if abs(self.error[Now]) > self.threshold["accel_limit_off"]:
            # When error is small, smooth control delays the convergence of drive.
            # When error is large, smooth control can avoid overshooting.
            max_diff = self.max_acceleration * self.dt
            # 0.2 clipping is to avoid large acceleration caused by large dt.
            speed = utils.clip(
                speed, current_speed - max_diff, current_speed + max_diff
            )  # Limit acceleration.
        speed = utils.clip(speed, -1 * self.max_speed, self.max_speed)  # Limit speed.

        if stop:
            utils.update_list(self.cmd_speed, 0)
        else:
            utils.update_list(self.cmd_speed, speed)

        return self.cmd_speed[Now]

    def _calc_pid(self) -> float:
        # Speed of the move of commanded coordinate. This includes sidereal motion, scan
        # speed, and other non-static component of commanded value.
        target_acceleration = (
            self.target_speed[Now] - self.target_speed[Last]
        ) / self.dt
        if abs(target_acceleration) > self.threshold["target_accel_ignore"]:
            self.target_speed[Now] = 0

        return (
            self.target_speed[Now]
            + self.k_p * self.error[Now]
            + self.k_i * self.error_integral
            + self.k_d * self.error_derivative
        )


def optimum_angle(
    current: float,
    target: float,
    limits: Tuple[float, float],
    margin: float = 40.0,  # 40 deg
    threshold_allow_360deg: float = 5.0,  # 5 deg
    unit: AngleUnit = "deg",
) -> float:
    """Find optimum unwrapped angle.

    Azimuthal control of telescope should avoid:

    1. 360deg motion during observation.
        This mean you should observe around -100deg, not 260deg, to command telescope of
        [-270, 270]deg limit.
    2. Over-180deg motion.
        Both 170deg and -190deg are safe in avoiding the 360deg motion, but if the
        telescope is currently directed at 10deg, you should select 170deg to save time.

    Parameters
    ----------
    current
        Current coordinate.
    target
        Target coordinate.
    limits
        Operation range of telescope drive.
    margin
        Safety margin around limits. While observations, this margin can be violated to
        avoid suspension of scan.
    threshold_allow_360deg
        If separation between current and target coordinates is larger than this value,
        360deg motion can occur. This parameter should be greater than the maximum size
        of a region which can be mapped in 1 observation.
    unit
        Physical unit of given arguments and return value of this function.

    Returns
    -------
    angle
        Unwrapped angle in the same unit as the input.

    Notes
    -----
    This is a utility function, so there's large uncertainty where this function
    finally settle in.
    This function will be executed in high frequency, so the use of
    ``utils.parse_quantity_once`` is avoided.

    Examples
    --------
    >>> optimum_angle(15, 200, limits=[-270, 270], margin=20, unit="deg")

    """
    assert limits[0] < limits[1], "Limits should be given in ascending order."
    deg = utils.angle_conversion_factor("deg", unit)
    turn = 360 * deg

    # Avoid 360deg motion while observing.
    if abs(target - current) < threshold_allow_360deg:
        return target

    target_candidate_min = target - turn * ((target - limits[0]) // turn)
    target_candidates = [
        angle
        for angle in utils.frange(target_candidate_min, limits[1], turn)
        if (limits[0] + margin) < angle < (limits[1] - margin)
    ]
    if len(target_candidates) == 1:
        # If there's only 1 candidate, return it, even if >180deg motion needed.
        return target_candidates[0]
    else:
        # Avoid over-180deg motion.
        optimum = [
            angle for angle in target_candidates if abs(angle - current) <= turn / 2
        ][0]
        return optimum
