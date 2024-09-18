__all__ = ["AZD_AD"]
import ogameasure
from astropy.units.quantity import Quantity

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

    def set_step(self, step: int, axis: str) -> None:
        return super().set_step(step, axis)

    def set_speed(self, speed: float, axis: str) -> None:
        return super().set_speed(speed, axis)

    def get_speed(self, axis: str) -> Quantity:
        return super().get_speed(axis)

    def get_step(self, axis: str) -> int:
        return super().get_step(axis)

    def finalize(self) -> None:
        return super().finalize()
