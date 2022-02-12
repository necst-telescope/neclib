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
from typing import Dict, Tuple

import numpy as np

from .. import utils
from ..typing import AngleUnit


# Indices for 2-lists (mutable version of so-called 2-tuple).
Last = -2
Now = -1
# Default value for 2-lists.
DefaultTwoList = [np.nan, np.nan]


class PIDController:
    """PID controller for telescope antenna.

    PID controller, a classical but sophisticated controller for system which has some
    delay on response to some input.

    Notes
    -----
    This controller adds constant term to the general PID formulation. This is an
    attempt to follow constant motions such as raster scanning and sidereal motion
    tracking.

    .. warning::

        When you are to assign ``ANGLE_UNIT`` other than its default value, ``deg``, you
        should fix the values of ``MAX_SPEED``, ``MAX_ACCELERATION``, and ``THRESHOLD``.

    Examples
    --------
    >>> controller = PIDController(pid_param=[1.5, 0, 0])
    >>> speed = controller.get_speed(target_coordinate, encoder_reading)

    """

    K_p: float = 1.0
    K_i: float = 0.5
    K_d: float = 0.3
    """Free parameters for PID."""

    ANGLE_UNIT: AngleUnit = "deg"
    """Unit in which all public functions accept as its argument and return."""

    MAX_SPEED: float = 2.0  # 2deg/s
    """Maximum speed for telescope motion."""
    MAX_ACCELERATION: float = 2.0  # 2deg/s^2
    """Maximum acceleration for telescope motion."""

    ERROR_INTEG_COUNT: int = 50
    """Number of error data to be stored for integral term calculation."""
    # Keep last 50 data for error integration.
    # Time interval of error integral varies according to PID calculation frequency,
    # which may cause optimal PID parameters to change according to the frequency.

    THRESHOLD: Dict[str, float] = {
        "cmd_coord_change": 100 / 3600,  # 100arcsec
        "accel_limit_off": 20 / 3600,  # 20arcsec
        "target_accel_ignore": 2,  # 2deg/s^2
    }
    """Thresholds for conditional executions."""

    def __init__(
        self,
        *,
        pid_param: Tuple[float, float, float] = None,
        max_speed: float = None,
        max_acceleration: float = None,
        error_integ_count: int = None,
        threshold: Dict[str, float] = None,
    ) -> None:
        self.k_p, self.k_i, self.k_d = self.K_p, self.K_i, self.K_d
        self.max_speed = self.MAX_SPEED
        self.max_acceleration = self.MAX_ACCELERATION
        self.error_integ_count = self.ERROR_INTEG_COUNT
        self.threshold = self.THRESHOLD.copy()

        if pid_param is not None:
            self.k_p, self.k_i, self.k_d = pid_param
        if max_speed is not None:
            self.max_speed = max_speed
        if max_acceleration is not None:
            self.max_acceleration = max_acceleration
        if error_integ_count is not None:
            self.error_integ_count = error_integ_count
        if threshold is not None:
            self.threshold.update(threshold)

        # Initialize parameters buffer.
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
        speed
            Speed which will be commanded to motor, in original unit.

        """
        delta_cmd_coord = cmd_coord - self.cmd_coord[Now]
        if np.isnan(self.time[Now]) or (
            abs(delta_cmd_coord) > self.threshold["cmd_coord_change"]
        ):
            self._set_initial_parameters(cmd_coord, enc_coord)
            # Set default values on initial run or on detection of sudden jump of error,
            # which may indicate a change of commanded coordinate.
            # This will give too small `self.dt` later, but that won't propose any
            # problem, since `current_speed` goes to 0, and too large target_speed will
            # be suppressed by speed and acceleration limit.

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
    margin: float = 40.0,
    threshold_allow_360deg: float = 5.0,
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

    Examples
    --------
    >>> optimum_angle(15, 200, limits=[-270, 270], margin=20, unit="deg")
    -160

    """
    assert limits[0] < limits[1], "Limits should be given in ascending order."
    deg2unit = utils.angle_conversion_factor("deg", unit)
    turn = 360 * deg2unit

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
