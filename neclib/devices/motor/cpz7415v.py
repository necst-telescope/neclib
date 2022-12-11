__all__ = ["CPZ7415V"]

import time
from typing import Dict, Literal

import astropy.units as u

from ... import get_logger, utils
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
        self.axis_mapping = dict(self.Config.axis.items())
        self.speed_to_pulse_factor = dict(self.Config.speed_to_pulse_factor.items())
        _config = {ax: getattr(self.Config, ax) for ax in self.use_axes}

        self.motion = {
            ax: dict(getattr(self.Config, f"{ax}_motion").items())
            for ax in self.use_axes
        }
        self.motion_mode = {ax: conf.mode for ax, conf in _config.items()}
        self.pulse_conf = {ax: conf.pulse_conf for ax, conf in _config.items()}
        self.default_speed = {ax: conf.motion_speed for ax, conf in _config.items()}
        self.low_speed = {ax: conf.motion_low_speed for ax, conf in _config.items()}

        self.last_direction = {ax: 0 for ax in self.use_axes}

        self.io = self._initialize_io()

    @utils.skip_on_simulator
    def _initialize_io(self):
        import pyinterface

        io = pyinterface.open(7415, self.rsw_id)
        if io is None:
            raise RuntimeError("Cannot communicate with the PCI board.")
        io.initialize()
        for ax in self.use_axes:
            if io.read_counter(ax, "counter") == 0:
                io.write_counter(ax, "counter", [1])  # HACK: Virtually escape origin
        for ax in self.use_axes:
            io.set_pulse_out(ax, "method", [self.pulse_conf[ax]])
        io.set_motion(self.use_axes, list(self.motion_mode.values()), self.motion)

        do = [int(self.motion_mode.get(ax, "") == "jog") for ax in "xyzu"]
        io.output_do(do)
        return io

    @property
    def current_motion(self) -> Dict[str, int]:
        status = map(int, self.io.driver.get_main_status(self.use_axes))
        return {ax: st for ax, st in zip(self.use_axes, status)}

    def _parse_ax(self, axis: str) -> Literal["x", "y", "z", "u"]:
        if axis in self.use_axes:
            return axis
        return self.axis_mapping[axis.lower()]

    def get_speed(self, axis: str) -> u.Quantity:
        ax = self._parse_ax(axis)
        with utils.busy(self, "_busy"):
            speed = self.io.read_speed(ax)[0]
            return speed / self.speed_to_pulse_factor[ax] * u.Unit("deg/s")

    def get_step(self, axis: str) -> int:
        ax = self._parse_ax(axis)
        with utils.busy(self, "_busy"):
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

    def set_step(self, step: int, axis: str) -> None:
        ax = self._parse_ax(axis)
        if self.motion_mode[ax] != "ptp":
            raise RuntimeError(
                "Position setting is only supported in point-to-point (ptp) mode, "
                f"but {axis=!r} is controlled in {self.motion_mode[ax]!r} mode."
            )
        if self.current_motion[ax] != 0:
            self._change_step(step, ax)
        else:
            speed = self.motion[ax]["speed"]
            self._start(speed, step, ax)

    def _change_step(self, step: int, axis: Literal["x", "y", "z", "u"]) -> None:
        with utils.busy(self, "_busy"):
            self.io.change_step(axis=axis, step=[step])

    def _change_speed(self, speed: float, axis: Literal["x", "y", "z", "u"]) -> None:
        with utils.busy(self, "_busy"):
            self.io.change_speed(axis=axis, mode="accdec_change", speed=[speed])

    def _start(
        self, speed: float, step: int, axis: Literal["x", "y", "z", "u"]
    ) -> None:
        self._stop(axis)
        with utils.busy(self, "_busy"):
            self.motion[axis]["speed"] = speed
            self.motion[axis]["step"] = int(step)

            axis_mode = [self.motion_mode[axis]]
            self.io.set_motion(axis=axis, mode=axis_mode, motion=self.motion)
            self.io.start_motion(
                axis=axis, start_mode="const", move_mode=self.motion_mode[axis]
            )

    def _stop(self, axis: Literal["x", "y", "z", "u"]) -> None:
        with utils.busy(self, "_busy"):
            self.io.stop_motion(axis=axis, stop_mode="immediate_stop")
            while int(self.io.driver.get_main_status(axis)[0][0]) != 0:
                time.sleep(1e-4)

    def finalize(self) -> None:
        self.io.output_do([0, 0, 0, 0])
        [self.set_speed(0, ax) for ax in self.use_axes]
