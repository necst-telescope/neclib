__all__ = ["AZD_AD"]
import time
from typing import Union

import ogameasure

from ... import get_logger
from ...core.security import busy
from .motor_base import Motor


class AZD_AD(Motor):
    """Pulse controller, which can handle up to 4 motors (axes)."""

    Model = "AZD_AD"
    Manufacturer = "OrientalMotor"

    Identifier = "host"

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

        host = self.Config.host
        gpibport = self.Config.port
        com = ogameasure.gpib_prologix(host, gpibport)
        self.motor = ogameasure.OrientalMotor.azd_ad(com)
        self.motor.zero_return()

    def set_step(self, step: Union[int, str], axis=None) -> None:
        if (step >= self.Config.low_limit) & (step <= self.Config.high_limit):
            self.motor.direct_operation(location=step)
        else:
            raise ValueError(f"Over limit range: {step}")
        return super().set_step(step, axis)

    def set_speed(self, speed=None, axis=None) -> None:
        raise RuntimeError(
            "This device don't have linear-uniform-motion mode."
            "Please use `set_step` function."
        )

    def get_step(self, axis=None) -> int:
        with busy(self, "busy"):
            step = self.motor.get_current_step()
            return step

    def get_speed(self, axis=None) -> None:
        raise NotImplementedError(
            "This device don't have linear-uniform-motion mode."
            "Please use `get_step` function."
        )

    def move_home_position(self) -> None:
        self.motor.zero_return()
        return

    def finalize(self) -> None:
        self.motor.zero_return()
        time.sleep(5)
        self.motor.com.close()
        return
