"""PID controller for telescope main dish.

.. note::

    This script will be executed in high frequency with no vectorization, and there are
    many arrays updated frequently. These mean that the use of Numpy may not be the best
    choice to speed up the calculation. Measure the execution time first, then
    implement.

"""

import time
from typing import Tuple

import numpy as np

from . import utils
from .typing import AngleUnit


# Indices for 2-lists (mutable version of so-called 2-tuple).
Last = -2
Now = -1
# Default value for 2-lists.
DefaultTwoList = [np.nan, np.nan]


class PIDController:
    r"""PID controller for telescope antenna.

    PID controller, a classical but sophisticated controller for system which has some
    delay on response to some input.

    Notes
    -----
    Suitable control parameter is calculated using a simple function consists of
    Proportional, Integral and Derivative terms:

    .. math::

        u(t) = K_\mathrm{p} \, e(t)
        + K_\mathrm{i} \int e(\tau) \, \mathrm{d}\tau
        + K_\mathrm{d} \frac{ \mathrm{d}e(t) }{ \mathrm{d}t }

    where :math:`K_\mathrm{p}, K_\mathrm{i}` and :math:`K_\mathrm{d}` are free
    parameters, :math:`u(t)` is the parameter to control, and :math:`e(t)` is the error
    between command value and actual value of reference parameter.

    This controller adds constant term to the above formulation. This is an attempt to
    follow constant motions such as raster scanning and sidereal motion tracking.

    """

    K_p: float = 1.0
    K_i: float = 0.5
    K_d: float = 0.3
    """Free parameter for PID."""

    ANGLE_UNIT: AngleUnit = "deg"
    """Unit in which all the function argument will be given, and all public functions
        return."""

    MAX_SPEED: float = 2.0
    """Maximum speed in ``ANGLE_UNIT`` per second."""
    MAX_ACCELERATION: float = 2.0
    """Maximum acceleration in ``ANGLE_UNIT`` per second squared."""

    ERROR_INTEG_COUNT: int = 50
    """Number of error data to be stored for integral term calculation."""
    # Keep last 50 data for error integration.
    # Time interval of error integral varies according to PID calculation frequency,
    # which may cause optimal PID parameters to change according to the frequency.

    def __init__(self) -> None:
        # Initialize parameters.
        self._initialize()
        self.factor_to_deg = utils.angle_conversion_factor(self.ANGLE_UNIT, "deg")
        self.factor_to_arcsec = utils.angle_conversion_factor(self.ANGLE_UNIT, "arcsec")

    @classmethod
    def with_configuration(
        cls,
        *,
        pid_param: Tuple[float, float, float] = None,
        max_speed: float = None,
        max_acceleration: float = None,
        error_integ_count: int = None,
        angle_unit: AngleUnit = None,
    ) -> "PIDController":
        """Initialize ``AntennaDevice`` class with properly configured parameters.

        Examples
        --------
        >>> AntennaDevice.with_configuration(pid_param=[2.2, 0, 0])

        """
        if pid_param is not None:
            cls.K_p, cls.K_i, cls.K_d = pid_param
        if max_speed is not None:
            cls.MAX_SPEED = max_speed
        if max_acceleration is not None:
            cls.MAX_ACCELERATION = max_acceleration
        if error_integ_count is not None:
            cls.ERROR_INTEG_COUNT = error_integ_count
        if angle_unit is not None:
            cls.ANGLE_UNIT = angle_unit
        return cls()

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

        utils.update_list(self.time, time.time())
        utils.update_list(self.cmd_coord, cmd_coord)
        utils.update_list(self.enc_coord, enc_coord)
        utils.update_list(self.error, cmd_coord - enc_coord)
        utils.update_list(self.target_speed, 0)

    def _initialize(self) -> None:
        if not hasattr(self, "cmd_speed"):
            self.cmd_speed = DefaultTwoList.copy()
        self.time = DefaultTwoList.copy() * int(self.ERROR_INTEG_COUNT / 2)
        self.cmd_coord = DefaultTwoList.copy()
        self.enc_coord = DefaultTwoList.copy()
        self.error = DefaultTwoList.copy() * int(self.ERROR_INTEG_COUNT / 2)
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
        threshold = 100 * self.factor_to_arcsec  # 100arcsec
        delta_cmd_coord = cmd_coord - self.cmd_coord[Now]
        if np.isnan(self.time[Now]) or (abs(delta_cmd_coord) > threshold):
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
        if abs(self.error[Now]) > 20 * self.factor_to_arcsec:  # 20arcsec
            # When error is small, smooth control delays the convergence of drive.
            # When error is large, smooth control can avoid overshooting.
            max_diff = utils.clip(self.MAX_ACCELERATION * self.dt, -0.2, 0.2)
            # 0.2 clipping is to avoid large acceleration caused by large dt.
            speed = utils.clip(
                speed, current_speed - max_diff, current_speed + max_diff
            )  # Limit acceleration.
        speed = utils.clip(speed, -1 * self.MAX_SPEED, self.MAX_SPEED)  # Limit speed.

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
        threshold = 2 * self.factor_to_deg
        if abs(target_acceleration) > threshold:
            self.target_speed[Now] = 0

        return (
            self.target_speed[Now]
            + self.K_p * self.error[Now]
            + self.K_i * self.error_integral
            + self.K_d * self.error_derivative
        )

    @classmethod
    def suitable_angle(
        cls,
        current: float,
        target: float,
        limits: Tuple[float, float],
        margin: float = 40.0,
        unit: AngleUnit = None,
    ) -> float:
        """Find suitable unwrapped angle.

        Returns
        -------
        angle
            Unwrapped angle in the same unit as the input.

        Notes
        -----
        Azimuthal control of telescope should avoid
        1. 360deg motion during observation. This mean you should observe around
        -100deg, not 260deg, to command telescope of [-270, 270]deg limit.
        2. Over-180deg motion. Both 170deg and -190deg are safe in avoiding the 360deg
        motion, but if the telescope is currently directed at 10deg, you should select
        170deg to save time.

        """
        if unit is None:
            unit = cls.ANGLE_UNIT
        assert limits[0] < limits[1], "Limits should be given in ascending order."
        turn = 360 * utils.angle_conversion_factor("deg", unit)

        # Avoid 360deg motion.
        target_min_candidate = target - turn * ((target - limits[0]) // turn)
        target_candidates = [
            angle
            for angle in utils.frange(target_min_candidate, limits[1], turn)
            if (limits[0] + margin) < angle < (limits[1] - margin)
        ]
        if len(target_candidates) == 1:
            return target_candidates[0]
        else:
            # Avoid over-180deg motion.
            suitable = [
                angle for angle in target_candidates if (angle - current) <= turn / 2
            ][0]
            return suitable
