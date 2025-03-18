__all__ = ["CPZ7415V"]

import time
import os
from typing import Dict, Literal, Union

import astropy.units as u

from ... import get_logger, utils
from ...core.security import busy
from .motor_base import Motor


class CPZ7415V(Motor):
    """Pulse controller, which can handle up to 4 motors (axes).

    Notes
    -----
    Configuration items for this device:

    rsw_id : {0, 1, ..., 16} or {"0", "1", ..., "9", "A", ..., "F"}
        Board identifier. This should be set to the same value as the rotary switch
        "RSW1" mounted on the side of the board. The board is shipped with default RSW1
        setting of 0. This ID would be non-zero, when multiple PCI board of same model
        are mounted on a single FA (Factory Automation) controller.
    useaxes : {"x", "y", "z", "u"} or concatenation of them
        Axes to control.
    {axis}_mode : {"jog", "org", "ptp", "timer", ...}
        Motion mode for the axis. ``"jog"`` for speed control, ``"ptp"`` for absolute
        position control.
    {axis}_pulse_conf : Dict[str, int]
        Keys should be ["PULSE", "OUT", "DIR", "WAIT", "DUTY"], and values should be 1
        or 0. If "PULSE" is 1, 2-pulse mode is used. If "OUT" is 1, output pulse is
        active-high. If "DIR" is 1, direction output is high when CCW motion (1-pulse
        mode), direction output is always low (2-pulse mode). If "WAIT" is 1, delay of
        200us is inserted on the direction change. If "DUTY" is 1, duty cycle is
        adaptively changed according to the speed, otherwise always 50%.
    {axis}_motion_clock : int
        Pulse frequency scale factor, valid values are 2 through 4095. The frequency is
        calculated by ``300 / (clock + 1)``.
    {axis}_motion_acc_mode : {"acc_normal", "acc_sin"}
        Acceleration mode. ``"acc_normal"`` for linear acceleration, ``"acc_sin"``
        for S-curve acceleration.
    {axis}_motion_low_speed : int
        Startup speed, valid values are 1 through 65535.
    {axis}_motion_speed : int
        Steady state speed, valid values are 1 through 65535. This will be used in
        "ptp" motion.
    {axis}_motion_acc : int
        Acceleration time, valid values are 1 through 65535.
    {axis}_motion_dec : int
        Deceleration time, valid values are 1 through 65535.
    {axis}_motion_step : int
        Number of pulses, used in "ptp" (valid values are -134217728 through 134217727),
        "org_search", "timer" (valid values are 1 through 134217727) motion. This
        setting is ignored in other modes.
    axis_{alias} : {"x", "y", "z", "u"}
        Mapping from the controller axes to telescope control axes. The ``{alias}``
        should be ["az", "el"].
    speed_to_pulse_factor_{axis} : float
        Conversion factor from speed to pulse frequency. This includes the gear ratio.
        For axes which won't be controlled in speed, there's no need to define this
        parameter for them.

    All parameters prefixed with ``{axis}_`` need to be defined for each axis in
    ``useaxes``.
    See http://www.interface.co.jp/download/tutorial/tut0053_14.pdf for details.

    """

    Manufacturer = "Interface"
    Model = "CPZ7415V"

    Identifier = "rsw_id"

    def __init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__)

        self.rsw_id = self.Config.rsw_id
        self.use_axes = self.Config.useaxes.lower()
        self.start_mode = self.Config.start_mode
        self.speed_to_pulse_factor = utils.AliasedDict(
            self.Config.speed_to_pulse_factor.items()
        )
        self.telescope = os.environ["TELESCOPE"]
        self.DI_list = {}
        for key, value in self.Config.DI_ch.item():
            if value is None:
                continue
            else:
                self.DI_list[key] = value - 1

        self.DO_list = {}
        for key, value in self.Config.DO_ch.item():
            if value is None:
                continue
            else:
                self.DO_list[key] = value - 1

        _config = {ax: getattr(self.Config, ax) for ax in self.use_axes}

        self.speed_to_pulse_factor.alias(
            **{v: k for k, v in self.Config.channel.items()}
        )

        self.motion = {
            ax: dict(getattr(self.Config, f"{ax}_motion").items())
            for ax in self.use_axes
        }
        self.motion_mode = {ax: conf.mode for ax, conf in _config.items()}
        self.pulse_conf = {ax: conf.pulse_conf for ax, conf in _config.items()}
        self.default_speed = {ax: conf.motion["speed"] for ax, conf in _config.items()}
        self.low_speed = {ax: conf.motion["low_speed"] for ax, conf in _config.items()}

        self.last_direction = {ax: 0 for ax in self.use_axes}

        self.io = self._initialize_io()

    @utils.skip_on_simulator
    def _initialize_io(self):
        import pyinterface

        io = pyinterface.open(7415, self.rsw_id)
        if io is None:
            raise RuntimeError("Cannot communicate with the PCI board.")

        count = [c if c != 0 else 1 for c in io.read_counter(self.use_axes, "counter")]
        io.initialize()
        do = [int(self.motion_mode.get(ax, "") == "jog") for ax in "xyzu"]
        io.output_do(do)

        for ax in self.use_axes:
            if self.telescope == "NANTEN2":
                if ax != self._parse_ax("chopper"):
                    # HACK: Escape from origin
                    io.write_counter(self.use_axes, "counter", [1] * len(self.use_axes))
                    io.write_counter(self.use_axes, "counter", count)
                    io.set_pulse_out(ax, "method", [self.pulse_conf[ax]])
                    io.set_motion(
                        self.use_axes, list(self.motion_mode.values()), self.motion
                    )
                else:
                    ax_motion = {ax: self.motion[ax]}
                    ax_mode = self.motion_mode[ax]
                    io.set_motion(ax, [ax_mode], {ax: ax_motion})
            elif self.telescope == "OMU1P85M":
                io.write_counter(self.use_axes, "counter", [1] * len(self.use_axes))
                io.write_counter(self.use_axes, "counter", count)
                io.set_pulse_out(ax, "method", [self.pulse_conf[ax]])
                io.set_motion(
                    self.use_axes, list(self.motion_mode.values()), self.motion
                )

        return io

    @property
    def current_motion(self) -> Dict[str, int]:
        status = map(int, self.io.driver.check_move_onoff(self.use_axes))
        return {ax: st for ax, st in zip(self.use_axes, status)}

    def _parse_ax(self, axis: str) -> Literal["x", "y", "z", "u"]:
        if axis.lower() in self.use_axes:
            return axis.lower()
        return self.Config.channel[axis.lower()]

    def get_speed(self, axis: str) -> u.Quantity:
        ax = self._parse_ax(axis)
        with busy(self, "_busy"):
            speed = self.io.read_speed(ax)[0]
            return speed / self.speed_to_pulse_factor[ax] * u.Unit("deg/s")

    def get_step(self, axis: str) -> int:
        ax = self._parse_ax(axis)
        with busy(self, "_busy"):
            return self.io.read_counter(ax, cnt_mode="counter")[0]

    def set_speed(self, speed: float, axis: str) -> None:
        ax = self._parse_ax(axis)
        speed *= self.speed_to_pulse_factor[ax]

        if abs(speed) < self.low_speed[ax]:
            self._stop(ax)
            self.last_direction[ax] = 0
            return
        if self.motion_mode[ax] == "jog":
            if (self.last_direction[ax] * speed > 0) and (self.current_motion[ax] != 0):
                self._change_speed(abs(speed), ax)
            else:
                direction = 1 if speed > 0 else -1
                step = direction  # Not an absolute position.
                self.last_direction[ax] = direction
                self._start(abs(speed), step, ax)
                time.sleep(1e-2)

    def set_step(self, step: Union[str, int], axis: str) -> None:
        ax = self._parse_ax(axis)
        if self.motion_mode[ax] != "ptp":
            raise RuntimeError(
                "Position setting is only supported in point-to-point (ptp) mode, "
                f"but {axis=!r} is controlled in {self.motion_mode[ax]!r} mode."
            )
        if isinstance(step, str):
            step = self.Config.position[step.lower()]
        elif isinstance(step, int):
            low_limit = self.Config.low_limit
            high_limit = self.Config.high_limit
            if (step < low_limit) & (high_limit < step):
                raise ValueError(f"Over limit range: {step}")
            else:
                pass

        if self.current_motion[ax] != 0:
            self._change_step(step, ax)
        else:
            speed = self.motion[ax]["speed"]
            self._start(speed, step, ax)

    def _change_step(self, step: int, axis: Literal["x", "y", "z", "u"]) -> None:
        with busy(self, "_busy"):
            self.io.change_step(axis=axis, step=[step])

    def _change_speed(self, speed: float, axis: Literal["x", "y", "z", "u"]) -> None:
        with busy(self, "_busy"):
            self.io.change_speed(axis=axis, mode="accdec_change", speed=[speed])

    def _start(
        self, speed: float, step: int, axis: Literal["x", "y", "z", "u"]
    ) -> None:
        self._stop(axis)
        with busy(self, "_busy"):
            self.motion[axis]["speed"] = speed
            self.motion[axis]["step"] = int(step)
            # from Kunizane Master thesis on the antena motion
            axis_mode = [self.motion_mode[axis]]
            if self.motion_mode[axis] == "ptp":
                self.io.set_motion(axis=axis, mode=axis_mode, motion=self.motion)
                self.io.start_motion(
                    axis=axis, start_mode=self.start_mode, move_mode="ptp"
                )

            elif self.motion_mode[axis] == "jog":
                self.motion[axis]["speed"] = int(
                    abs(5e-3 * self.speed_to_pulse_factor[axis])
                )
                self.io.set_motion(axis=axis, mode=axis_mode, motion=self.motion)
                self.io.start_motion(axis=axis, start_mode="const", move_mode="jog")
                time.sleep(0.02)
                self.motion[axis]["speed"] = speed
                self.io.change_speed(
                    axis=axis, mode="accdec_change", speed=[abs(speed)]
                )

    def _stop(self, axis: Literal["x", "y", "z", "u"]) -> None:
        self.logger.debug(f"Stopping {axis=}. May indicate drive direction reversal.")
        with busy(self, "_busy"):
            self.io.stop_motion(axis=axis, stop_mode="immediate_stop")
            while int(self.io.driver.get_main_status(axis)[0][0]) != 0:
                time.sleep(1e-4)

    def finalize(self) -> None:
        try:
            for ax in self.use_axes:
                self._stop(ax)
        finally:
            self.io.output_do([0, 0, 0, 0])

    def check_status(self) -> list:
        status_io = self.io.input_di()
        ret_status_str = []
        try:
            if status_io[self.DI_list.get("ready")] == 1:
                ret_status_str.append("READY")
            else:
                ret_status_str.append("NOT READY")
        except KeyError:
            pass
        try:
            if status_io[self.DI_list.get("move")] == 1:
                ret_status_str.append("MOVE")
            else:
                ret_status_str.append("NOT MOVE")
        except KeyError:
            pass
        try:
            if status_io[self.DI_list.get("alarm")] == 1:
                ret_status_str.append("NO ALARM")
            else:
                ret_status_str.append("[CAUTION] ALARM")
        except KeyError:
            pass

        return ret_status_str

    def chopper_zero_point(self) -> None:
        list_zero_point = [0, 0, 0, 0]
        list_zero_point[self.DO_list.get("zeropoint")] = 1

        # set to all zero mode
        self.io.output_do([0, 0, 0, 0])
        time.sleep(1 / 10)

        # start moving to zero point
        self.io.output_do(list_zero_point)
        time.sleep(1)

        # waiting when slider stops.
        move_index = self.DI_list.get("ready")
        time0 = time.time()
        while time.time() - time0 < 3:
            time.sleep(0.5)
            if move_index is not None:
                if self.io.input_di([move_index]) == 0:
                    break
        self.logger.warning(
            "The process ended automatically because 3 seconds have passed."
        )

        self.io.output_do([0, 0, 0, 0])
        self.io.write_counter("u", "counter", [0])

    def remove_alarm(self) -> None:
        list_remove_alarm = [0, 0, 0, 0]
        list_remove_alarm[self.DO_list.get("removealarm")] = 1
        self.io.output_do(list_remove_alarm)
        time.sleep(1 / 10)
        self.io.output_do([0, 0, 0, 0])
