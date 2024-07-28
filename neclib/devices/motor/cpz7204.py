__all__ = ["CPZ7204"]

import time

import astropy.units as u

from ... import get_logger, utils
from .motor_base import Motor


class CPZ7204(Motor):
    Manufacturer = "Interface"
    Model = "CPZ7204"

    Identifier = "rsw_id"

    def __init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__)
        self.rsw_id = self.Config.rsw_id
        self.io = self._initialize_io()

    @utils.skip_on_simulator
    def _initialize_io(self):
        import pyinterface

        io = pyinterface.open(7204, self.rsw_id)
        if io is None:
            raise RuntimeError("Cannot communicate with the PCI board.")
        io.initialize()

        return io

    def set_step(self, position: str) -> None:
        self.move(position)
        return

    def get_step(self) -> str:
        status = self.io.get_status()
        if status["busy"]:
            position = "MOVE"
        elif status["limit"]["+EL"] == 0:
            position = "OUT"
        elif status["limit"]["-EL"] == 0:
            position = "IN"
        else:
            self.logger.warning("limit error")
            position = "ERROR"
        return position

    def move(self, position: str) -> None:
        if position == "OUT":
            step = 1
            self.logger.info("m4 move out")
        elif position == "IN":
            step = -1
            self.logger.info("m4 move in")
        else:
            self.logger.warning("parameter error")
            return
        self.io.set_motion(
            mode="JOG",
            acc_mode="SIN",
            low_speed=100,
            speed=1000,
            acc=500,
            step=step,
            axis=1,
        )
        self.io.start_motion(mode="JOG")
        self.logger.info("start_motion")
        time.sleep(0.5)
        return

    def stop(self, mode: str) -> None:
        # mode: "DEC", "IMMEDIATE"
        self.io.stop_motion(mode, 1)
        return

    def finalize(self) -> None:
        self.io.output_do([0, 0, 0, 0], 1)

    def set_speed(self, speed: float, axis: str) -> None:
        pass

    def get_speed(self, axis: str) -> u.Quantity:
        pass
