r"""PID controller for telescope main dish."""

__all__ = ["PIDController"]

import time as pytime
from contextlib import contextmanager
from typing import ClassVar, Dict, Generator, Literal, Optional, Tuple, Union

import astropy.units as u
import numpy as np
from scipy.interpolate import interp1d

from .. import utils
from ..core import math
from ..core.types import AngleUnit
from ..data import LinearExtrapolate
from ..utils import ParameterList

Last = -2
Now = -1

DefaultK_p = 1.0
DefaultK_i = 0.5
DefaultK_d = 0.3
DefaultMaxSpeed = 1.6 << u.deg / u.s
DefaultMaxAcceleration = 1.6 << u.deg / u.s**2
DefaultErrorIntegCount = 50
DefaultCmdTimeChangeSec = 6.0
DefaultIIntegStartError = 60 << u.arcsec  # type: ignore
DefaultIIntegResetError = 120 << u.arcsec  # type: ignore

DefaultThreshold = {
    "cmd_coord_change": 400 << u.arcsec,  # type: ignore
    "accel_limit_off": 20 << u.arcsec,  # type: ignore
    "target_accel_ignore": 2 << u.deg / u.s**2,
}

ThresholdKeys = Literal[
    "cmd_coord_change",
    "accel_limit_off",
    "target_accel_ignore",
]


class PIDController:
    ANGLE_UNIT: ClassVar[AngleUnit] = "deg"

    def __init__(
        self,
        *,
        pid_param: Tuple[float, float, float] = (
            DefaultK_p,
            DefaultK_i,
            DefaultK_d,
        ),
        max_speed: Union[str, u.Quantity] = DefaultMaxSpeed,
        max_acceleration: Union[str, u.Quantity] = DefaultMaxAcceleration,
        error_integ_count: int = DefaultErrorIntegCount,
        cmd_time_change_sec: Union[float, str, u.Quantity] = (DefaultCmdTimeChangeSec),
        i_integ_start_error: Union[str, u.Quantity] = (DefaultIIntegStartError),
        i_integ_reset_error: Union[str, u.Quantity] = (DefaultIIntegResetError),
        threshold: Dict[ThresholdKeys, Union[str, u.Quantity]] = DefaultThreshold,
    ) -> None:
        self.k_p, self.k_i, self.k_d = pid_param
        self.k_c = 1

        self.max_speed = utils.parse_quantity(
            max_speed,
            unit=self.ANGLE_UNIT,
        ).value

        self.max_acceleration = utils.parse_quantity(
            max_acceleration,
            unit=self.ANGLE_UNIT,
        ).value

        self.error_integ_count = error_integ_count

        if isinstance(cmd_time_change_sec, u.Quantity):
            self.cmd_time_change_sec = float(
                cmd_time_change_sec.to_value(u.s),
            )
        elif isinstance(cmd_time_change_sec, str):
            self.cmd_time_change_sec = float(
                utils.parse_quantity(
                    cmd_time_change_sec,
                    unit="s",
                ).value,
            )
        else:
            self.cmd_time_change_sec = float(cmd_time_change_sec)

        self.i_integ_start_error = utils.parse_quantity(
            i_integ_start_error,
            unit=self.ANGLE_UNIT,
        ).value

        self.i_integ_reset_error = utils.parse_quantity(
            i_integ_reset_error,
            unit=self.ANGLE_UNIT,
        ).value

        merged_threshold = DefaultThreshold.copy()
        merged_threshold.update(threshold)

        self.threshold = {
            key: utils.parse_quantity(val, unit=self.ANGLE_UNIT).value
            for key, val in merged_threshold.items()
        }

        self.coord_extrapolate = LinearExtrapolate(
            align_by="time",
            attrs=["time", "coord"],
        )

        self._initialize()

    @property
    def dt(self) -> float:
        return self.enc_time[Now] - self.enc_time[Last]

    @property
    def error_integral(self) -> float:
        time_arr = np.array(self.enc_time)
        error_arr = np.array(self.error_i)

        dt = time_arr[1:] - time_arr[:-1]
        interp = (error_arr[1:] + error_arr[:-1]) / 2

        return float(np.nansum(interp * dt))

    @property
    def error_derivative(self) -> float:
        return (self.error[Now] - self.error[Last]) / self.dt

    def _initialize(self) -> None:
        if not hasattr(self, "cmd_speed"):
            self.cmd_speed = ParameterList.new(2)

        size = 2 * int(self.error_integ_count / 2)

        self.cmd_time = ParameterList.new(50)
        self.enc_time = ParameterList.new(size)
        self.cmd_coord = ParameterList.new(50)
        self.enc_coord = ParameterList.new(size)
        self.error = ParameterList.new(size)
        self.error_i = ParameterList.new(size)
        self.target_speed = ParameterList.new(50)

        if not hasattr(self, "_i_enabled"):
            self._i_enabled = False

    def _reset_i_history(self) -> None:
        size = 2 * int(self.error_integ_count / 2)
        self.error_i = ParameterList.new(size)

        for _ in range(size):
            self.error_i.push(0)

    def get_speed(
        self,
        cmd_coord: float,
        enc_coord: float,
        stop: bool = False,
        *,
        cmd_time: Optional[float] = None,
        enc_time: Optional[float] = None,
    ) -> float:
        now = pytime.time()

        cmd_time_val = now if cmd_time is None else float(cmd_time)
        enc_time_val = now if enc_time is None else float(enc_time)

        delta_cmd = cmd_coord - self.cmd_coord[Now]

        time_disc = False

        if not np.isnan(self.cmd_time[Now]):
            if abs(cmd_time_val - self.cmd_time[Now]) > self.cmd_time_change_sec:
                time_disc = True

        if not np.isnan(self.enc_time[Now]):
            if abs(enc_time_val - self.enc_time[Now]) > self.cmd_time_change_sec:
                time_disc = True

        reasons = []

        if np.isnan(self.cmd_time[Now]):
            reasons.append("nan_cmd_time")

        if np.isnan(self.enc_time[Now]):
            reasons.append("nan_enc_time")

        if abs(delta_cmd) > self.threshold["cmd_coord_change"]:
            reasons.append(f"large_jump:{float(delta_cmd)}")

        if time_disc:
            reasons.append("time_discontinuity")

        if reasons:
            print(
                "[PID reset] "
                f"reason={reasons}, "
                f"cmd={cmd_coord}, prev_cmd={self.cmd_coord[Now]}, "
                f"enc={enc_coord}, prev_enc={self.enc_coord[Now]}"
            )

            self._set_initial_parameters(
                cmd_coord,
                enc_coord,
                reset_cmd_speed=time_disc,
                cmd_time_seed=cmd_time_val,
                enc_time_seed=enc_time_val,
            )

        current_speed = self.cmd_speed[Now]

        self.enc_time.push(enc_time_val)
        self.enc_coord.push(enc_coord)

        self.cmd_time.push(cmd_time_val)
        self.cmd_coord.push(cmd_coord)

        error, _ = self._calc_err()
        self.error.push(error)

        abs_err = abs(error)

        if self._i_enabled:
            if abs_err >= self.i_integ_reset_error:
                self._i_enabled = False
                self._reset_i_history()
                self.error_i.push(0)
            else:
                self.error_i.push(error)
        else:
            if abs_err <= self.i_integ_start_error:
                self._i_enabled = True
                self._reset_i_history()
                self.error_i.push(error)
            else:
                self.error_i.push(0)

        self.target_speed.push(
            (self.cmd_coord[Now] - self.cmd_coord[Last])
            / (self.cmd_time[Now] - self.cmd_time[Last])
        )

        speed = self._calc_pid()

        if abs(self.error[Now]) > self.threshold["accel_limit_off"]:
            max_diff = max(0.0, abs(self.max_acceleration) * self.dt)
            speed = math.clip(
                speed,
                current_speed - max_diff,
                current_speed + max_diff,
            )

        speed = math.clip(speed, abs(self.max_speed))

        accel = (speed - self.cmd_speed[Now]) / self.dt

        if abs(accel) > self.max_acceleration:
            max_diff = max(0.0, abs(self.max_acceleration) * self.dt)
            speed = math.clip(
                speed,
                current_speed - max_diff,
                current_speed + max_diff,
            )

        self.cmd_speed.push(0.0 if stop else speed)
        return self.cmd_speed[Now]

    def _calc_err(self):
        cmd = np.array(self.cmd_coord)
        cmd_time = np.array(self.cmd_time)

        valid = cmd_time < self.enc_time[Now]
        cmd_time = cmd_time[valid]

        if len(cmd_time) < 2:
            cmd_time = cmd_time[-2:]
            cmd = cmd[-2:]
        else:
            cmd = cmd[: len(cmd_time)]
            cmd_time = cmd_time[-2:]
            cmd = cmd[-2:]

        f = interp1d(cmd_time, cmd, fill_value="extrapolate")
        ext = float(f(self.enc_time[Now]))

        return ext - self.enc_coord[Now], ext

    def _calc_pid(self) -> float:
        accel = (self.target_speed[Now] - self.target_speed[Last]) / (
            self.cmd_time[Now] - self.cmd_time[Last]
        )

        target_speed = self.target_speed[Now]

        if abs(accel) > self.threshold["target_accel_ignore"]:
            target_speed = 0.0

        return (
            self.k_c * target_speed
            + self.k_p * self.error[Now]
            + self.k_i * self.error_integral
            + self.k_d * self.error_derivative
        )

    @contextmanager
    def params(self, **kwargs) -> Generator[None, None, None]:
        original = {
            "k_p": self.k_p,
            "k_i": self.k_i,
            "k_d": self.k_d,
            "k_c": self.k_c,
            "max_speed": self.max_speed,
            "max_acceleration": self.max_acceleration,
            "error_integ_count": self.error_integ_count,
            "cmd_time_change_sec": self.cmd_time_change_sec,
            "i_integ_start_error": self.i_integ_start_error,
            "i_integ_reset_error": self.i_integ_reset_error,
        }

        original_threshold = self.threshold.copy()

        for key, val in kwargs.items():
            if key in original:
                setattr(self, key, val)
            elif key in original_threshold:
                self.threshold[key] = val
            else:
                raise ValueError(f"Invalid parameter: {key}")

        try:
            yield
        finally:
            for key, val in original.items():
                setattr(self, key, val)

            self.threshold.update(original_threshold)
