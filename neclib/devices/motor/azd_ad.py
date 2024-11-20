__all__ = ["AZD_AD"]
import time
from typing import Union

import ogameasure

from ... import get_logger
from ...core.security import busy
from .motor_base import Motor


class AZD_AD(Motor):
    """Motor Controller for device of Oriental Motor

    Notes
    -----

    This code is used for direct operating of Oriental Motor Driver
    by using network converter (RS485 <-> Ethernet).
    For wiring and setup, please check the manual of this device.

    Configuration items for this device:

    host : str
        IP address for ethernet communicator.
        If you use LAN communicator, you must set this parameter.

    port : int
        Ethernet port of using devices. Please check device setting.
        If you use LAN communicator, you must set this parameter.

    position :Dict[str, int]
        Human-readable Position and step dictionary. The value should
        be mapping from human readable version (str) to device level
        identifier (int). You can assign any name to the step.
        For example: {insert = 8000, remove = 20000}

    velocity : int
        Motor velocity.
    low_limit : int
        Lower limit of motor motion.
    high_limit : int
        Higher limit of motor motion.
    """

    Model = "AZD_AD"
    Manufacturer = "OrientalMotor"

    Identifier = "host"

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

        host = self.Config.host
        port = self.Config.port
        com = ogameasure.ethernet(host, port)
        self.motor = ogameasure.OrientalMotor.azd_ad(com)
        self.motor.initialize()
        self.velocity = self.Config.velocity

    def set_step(self, step: Union[int, str], axis=None) -> None:
        if isinstance(step, str):
            step = self.Config.position[step.lower()]
        if (step >= self.Config.low_limit) & (step <= self.Config.high_limit):
            self.motor.direct_operation(location=step, speed=self.velocity)
        else:
            raise ValueError(f"Over limit range: {step}")
        return

    def set_speed(self, speed=None, axis=None) -> None:
        raise RuntimeError(
            "This device don't have linear-uniform-motion mode."
            "Please use `set_step` function."
        )

    def get_step(self, axis=None) -> int:
        with busy(self, "busy"):
            step = self.motor.get_current_position()
            return step

    def get_speed(self, axis=None) -> None:
        raise NotImplementedError(
            "This device don't have linear-uniform-motion mode."
            "Please use `get_step` function."
        )

    def move_home(self) -> None:
        self.motor.zero_return()
        return

    def get_alarm(self) -> str:
        alarm = self.motor.alarm_query()
        return alarm

    def reset_alarm(self) -> None:
        self.motor.alarm_reset()
        return

    def finalize(self) -> None:
        self.motor.zero_return()
        time.sleep(5)
        self.motor.com.close()
        return

    def close(self) -> None:
        self.motor.com.close()
