"""Emulator for telescope antenna motion and corresponding encoder reading."""

__all__ = ["AntennaEncoderEmulator"]

import time
from typing import Callable, ClassVar, List, Literal, Tuple, Union

import astropy.units as u
import numpy as np

from .. import utils
from ..typing import AngleUnit
from ..utils import AzElData, ParameterList

# Indices for parameter lists.
Last = -2
Now = -1

DefaultMomentOfInertia = [
    lambda az, el: (2500 + 3000 * np.cos(el)) * u.Unit("kg m2"),
    3000 * u.Unit("kg m2"),
]  # NANTEN2, rough estimation based on Ito (2005), Master's thesis.
DefaultMotorTorque = [11.5 * u.Unit("N m"), 11.5 * u.Unit("N m")]
# NANTEN2, from Ito (2005), Master's thesis.
DefaultAngularResolution = [
    360 * 3600 / (23600 * 400) * u.arcsec,
    360 * 3600 / (23600 * 400) * u.arcsec,
]  # RENISHAW RESM series encoder, which is installed in NANTEN2.

InitialPosition = AzElData(180 << u.deg, 45 << u.deg)

QtyFn = Union[u.Quantity, Callable[[u.Quantity, u.Quantity], u.Quantity]]


class AntennaEncoderEmulator:
    """Emulator of antenna response for simulator.

    Parameters
    ----------
    device_moment_of_inertia
        Moment of inertia of antenna.
    motor_torque
        Maximum torque the motor can exert.
    angular_resolution
        Angular resolution of the encoder.

    Notes
    -----
    To support coordinate-dependent moment of inertia, Az. and El. axes cannot
    independently be implemented.

    .. warning::

        API may change, as API of encoder driver module isn't fixed yet.

    Example
    -------
    >>> enc = neclib.simulators.AntennaEncoderEmulator()
    >>> pid_az = neclib.controllers.PIDController()
    >>> speed = pid_az.get_speed(30, enc.read.az)
    >>> enc.command(speed, "az")

    """

    ANGLE_UNIT: ClassVar[AngleUnit] = "deg"

    def __init__(
        self,
        device_moment_of_inertia: Tuple[QtyFn, QtyFn] = DefaultMomentOfInertia,
        motor_torque: Tuple[u.Quantity, u.Quantity] = DefaultMotorTorque,
        angular_resolution: Tuple[u.Quantity, u.Quantity] = DefaultAngularResolution,
    ) -> None:
        device_moment_of_inertia = self._make_callable(device_moment_of_inertia)

        # Force the use of SI unit
        device_moment_of_inertia = [
            lambda az, el: func(az, el).si.value for func in device_moment_of_inertia
        ]
        motor_torque = [qty.si.value for qty in motor_torque]
        angular_resolution = [
            qty.to(self.ANGLE_UNIT).value for qty in angular_resolution
        ]

        self.moment_of_inertia = AzElData(*device_moment_of_inertia)
        self.torque = AzElData(*motor_torque)
        self.angular_resolution = AzElData(*angular_resolution)

        self.time = ParameterList.new(2, time.time())
        self.position = AzElData(
            InitialPosition.az.to(self.ANGLE_UNIT).value,
            InitialPosition.el.to(self.ANGLE_UNIT).value,
        )
        self.speed = AzElData(0, 0)
        self.cmd_speed = AzElData(0, 0)

        # Conversion factor for fluctuation and angular acceleration scaling.
        self.rad = utils.angle_conversion_factor("rad", self.ANGLE_UNIT)
        self.arcsec = utils.angle_conversion_factor("arcsec", self.ANGLE_UNIT)

    @staticmethod
    def _make_callable(value_or_function: List[QtyFn]) -> QtyFn:
        """Make common interface for value acquisition."""
        return [
            item if callable(item) else lambda az, el: item
            for item in value_or_function
        ]

    @property
    def abs_acceleration(self) -> AzElData:
        """Absolute value of angular acceleration at the moment."""
        try:
            return AzElData(
                self.torque.az
                / self.moment_of_inertia.az(self.position.az, self.position.el)
                * self.rad,
                self.torque.el
                / self.moment_of_inertia.el(self.position.az, self.position.el)
                * self.rad,
            )
        except ZeroDivisionError:
            small_mom_of_inertia = 1e-8
            return AzElData(
                self.torque.az / small_mom_of_inertia * self.rad,
                self.torque.el / small_mom_of_inertia * self.rad,
            )

    @property
    def dt(self) -> float:
        """Time interval between last two call for encoder reading."""
        return self.time[Now] - self.time[Last]

    def read(self) -> AzElData:
        """Get current encoder reading.

        Notes
        -----
        Acceleration during consecutive calls are approximated to be constant.

        Examples
        --------
        >>> v = enc.read()
        >>> v.az
        12.3

        """
        abs_accel = self.abs_acceleration
        now = time.time()
        self.time.push(now)

        accel = AzElData(
            np.sign(self.cmd_speed.az - self.speed.az) * abs_accel.az,
            np.sign(self.cmd_speed.el - self.speed.el) * abs_accel.el,
        )
        _speed = AzElData(
            self.speed.az + accel.az * self.dt,
            self.speed.el + accel.el * self.dt,
        )  # No consideration on the behavior when current speed reached the command.
        sped_over = AzElData(
            max(0, abs(_speed.az) - abs(self.cmd_speed.az)),
            max(0, abs(_speed.el) - abs(self.cmd_speed.el)),
        )  # How much over-sped when constant acceleration is assumed.
        accel0_duration = AzElData(
            sped_over.az / abs_accel.az, sped_over.el / abs_accel.el
        )  # How long the acceleration should be set to 0 to sustain command speed.
        next_position = AzElData(
            accel.az * self.dt**2 / 2
            + self.speed.az * self.dt
            + self.position.az
            - sped_over.az * accel0_duration.az / 2,
            accel.el * self.dt**2 / 2
            + self.speed.el * self.dt
            + self.position.el
            - sped_over.el * accel0_duration.el / 2,
        )

        self.speed.az = utils.clip(_speed.az, absmax=self.cmd_speed.az)
        self.speed.el = utils.clip(_speed.el, absmax=self.cmd_speed.el)
        self.position.az = next_position.az
        self.position.el = next_position.el

        fluctuation = np.random.randn
        return AzElData(
            utils.discretize(
                fluctuation() * self.arcsec + self.position.az,
                step=self.angular_resolution.az,
            ),
            utils.discretize(
                fluctuation() * self.arcsec + self.position.el,
                step=self.angular_resolution.el,
            ),
        )

    def command(self, speed: float, axis: Literal["az", "el"]) -> None:
        """Set angular speed of intention with angular unit ``ANGLE_UNIT``.

        Parameters
        ----------
        speed
            Angular speed, which may be calculated by PID controller.
        axis
            Controlling altazimuth axis.

        """
        setattr(self.cmd_speed, axis, speed)
