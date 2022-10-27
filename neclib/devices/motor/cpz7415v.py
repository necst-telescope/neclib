__all__ = ["CPZ7415V"]

import queue
import time
from threading import Event, Thread
from typing import Literal, Tuple

from .pulse_controller_base import PulseController
from ...exceptions import ConfigurationError
from ... import config, get_logger, utils


class CPZ7415V(PulseController):
    """Pulse controller, which can handle up to 4 motors (axes).

    - rsw_id
        Board identifier, set by rotary switch with label "RSW1" mounted on the side of
        the board. The board is shipped with default RSW1 setting of 0. This ID would be
        non-zero, when multiple PCI board of same model are mounted on a single FA
        (Factory Automation) controller. Accepted values are ``[0, 1, ..., 16]`` if
        given as ``int``, ``["0", "1", ..., "9", "A", ..., "F"]`` if ``str``.
    - other parameters
        See <http://www.interface.co.jp/download/tutorial/tut0053_14.pdf>.

    """

    Manufacturer = "Interface"
    Model = "CPZ7415V"

    CommandQueueMaxSize = {"warning": 10, "fatal": 30}

    def __init__(self) -> None:
        if config.antenna_cpz7415v is None:
            raise ConfigurationError("Parameters for CPZ-7415V not configured at all.")

        self.logger = get_logger(__name__)

        self.rsw_id = int(config.antenna_cpz7415v_rsw_id)
        self.do_status = config.antenna_cpz7415v_do_conf
        self.use_axes = config.antenna_cpz7415v_useaxes.lower()
        self.axis_mapping = config.antenna_cpz7415v_axis.__dict__
        _config = {
            ax: getattr(config, f"antenna_cpz7415v_{ax}") for ax in self.use_axes
        }

        self.motion = {
            ax: getattr(config, f"antenna_cpz7415v_{ax}_motion").__dict__
            for ax in self.use_axes
        }

        self.current_speed = {ax: 0 for ax in self.use_axes}
        self.current_step = {ax: 0 for ax in self.use_axes}
        self.current_moving = {ax: 0 for ax in self.use_axes}
        self.last_direction = {ax: 0 for ax in self.use_axes}

        self.mode = [conf.mode for conf in _config.values()]  # List type, for utility.
        self.move_mode = {ax: conf.mode for ax, conf in _config.items()}
        self.pulse_conf = {ax: conf.pulse_conf for ax, conf in _config.items()}
        self.default_speed = {ax: conf.motion_speed for ax, conf in _config.items()}
        self.low_speed = {ax: conf.motion_low_speed for ax, conf in _config.items()}

        self.task_queue = queue.Queue()

        self.io = self._initialize_io()
        self.thread = self._start_background_process()

    @utils.skip_on_simulator
    def _initialize_io(self):
        import pyinterface

        io = pyinterface.open(7415, self.rsw_id)
        for ax in self.use_axes:
            io.set_pulse_out(ax, "method", [self.pulse_conf[ax]])
        io.set_motion(self.use_axes, self.mode, self.motion)
        io.output_do([1, 1, 0, 0])
        return io

    def _start_background_process(self) -> Thread:
        self._stop_event = Event()
        thread = Thread(target=self._consume_task_queue, daemon=True)
        thread.start()
        return thread

    def _stop_background_process(self) -> None:
        event = getattr(self, "_stop_event", None)
        if event is not None:
            event.set()
            self._stop_event = None

    @utils.skip_on_simulator
    def _consume_task_queue(self) -> None:
        while not self._stop_event.is_set():
            speed = self.io.read_speed(self.use_axes)
            step = self.io.read_counter(self.use_axes, cnt_mode="counter")
            moving = [int(s[0]) for s in self.io.driver.get_main_status(self.use_axes)]

            self.current_speed = {ax: v for ax, v in zip(self.use_axes, speed)}
            self.current_step = {ax: v for ax, v in zip(self.use_axes, step)}
            self.current_moving = {ax: v for ax, v in zip(self.use_axes, moving)}

            if not self.task_queue.empty():
                if self._check_realtimeness(self.task_queue):
                    task = self.task_queue.get()
                    task["func"](task["args"], task["axis"])
                else:
                    # Commands in task_queue are too outdated, so it's dangerous to
                    # execute them.
                    _ = [self._stop(None, ax) for ax in self.use_axes]
            time.sleep(1e-5)

    def _check_realtimeness(self, queue_: queue.Queue) -> bool:
        qsize = queue_.qsize()
        if qsize < self.CommandQueueMaxSize["warning"]:
            return True
        elif qsize < self.CommandQueueMaxSize["fatal"]:
            self.logger.warning(
                f"{qsize} commands remain unprocessed. "
                "Consider reducing command frequency `antenna_command_frequency`."
            )
            return True
        else:
            self.logger.fatal(f"{qsize} commands remain unprocessed. Emergency stop...")
            return False

    def _convert_ax(self, axis: Literal["az", "el"]) -> str:
        if axis in self.use_axes:
            return axis
        return self.axis_mapping[axis.lower()]

    def set_step(self, step: int, axis: str) -> None:
        ax = self._convert_ax(axis)
        if self.move_mode[ax] == "ptp":
            if self.current_moving[ax] != 0:
                self.task_queue.put(
                    {"func": self._change_step, "args": step, "axis": ax}
                )
            else:
                speed_step = [self.motion[ax]["speed"], step]
                self.task_queue.put(
                    {"func": self._start, "args": speed_step, "axis": ax}
                )

    def set_speed(self, speed: float, axis: Literal["az", "el"]) -> None:
        ax = self._convert_ax(axis)
        speed *= getattr(config.antenna_speed_to_pulse_factor, axis).to_value("s/deg")

        if abs(speed) < self.low_speed[ax]:
            self.task_queue.put({"func": self._stop, "args": None, "axis": ax})
            self.last_direction[ax] = 0
            return
        if self.move_mode[ax] == "jog":
            if (self.last_direction[ax] * speed > 0) and (self.current_moving[ax] != 0):
                self.task_queue.put(
                    {"func": self._change_speed, "args": abs(speed), "axis": ax}
                )
            else:
                direction = 1 if speed > 0 else -1
                speed_step = [abs(speed), direction]
                self.last_direction[ax] = direction
                self.task_queue.put(
                    {"func": self._start, "args": speed_step, "axis": ax}
                )
                time.sleep(0.01)
        return

    def set_do_status(self, status: Tuple[int, int, int, int], do_num: int) -> None:
        self.do_status[do_num - 1] = status
        self.task_queue.put(
            {"func": self._output_do, "args": self.do_status, "axis": None}
        )

    @utils.skip_on_simulator
    def _stop(self, _, ax: str) -> None:
        self.io.stop_motion(axis=ax, stop_mode="immediate_stop")
        while int(self.io.driver.get_main_status(ax)[0][0]) != 0:
            time.sleep(1e-5)

    @utils.skip_on_simulator
    def _change_step(self, step: int, ax: str) -> None:
        self.io.change_step(axis=ax, step=[step])

    @utils.skip_on_simulator
    def _change_speed(self, speed: float, ax: str) -> None:
        self.io.change_speed(axis=ax, mode="accdec_change", speed=[speed])

    @utils.skip_on_simulator
    def _start(self, args, ax) -> None:
        self._stop(None, ax=ax)
        self.motion[ax]["speed"] = args[0]
        self.motion[ax]["step"] = int(args[1])

        axis_mode = [self.move_mode[ax]]
        self.io.set_motion(axis=ax, mode=axis_mode, motion=self.motion)
        self.io.start_motion(axis=ax, start_mode="const", move_mode=self.move_mode[ax])

    @utils.skip_on_simulator
    def _output_do(self, args, _) -> None:
        self.io.output_do(args)

    def get_speed(self, axis: Literal["az", "el"]) -> float:
        ax = self._convert_ax(axis)
        return self.current_speed[ax]

    def get_step(self, axis: Literal["az", "el"]) -> int:
        ax = self._convert_ax(axis)
        return int(self.current_step[ax])

    def finalize(self) -> None:
        self._output_do([0, 0, 0, 0], None)
