from abc import abstractmethod
from typing import Literal

import astropy.units as u

from ..device_base import DeviceBase


class Motor(DeviceBase):

    Manufacturer: str = ""
    Model: str

    @abstractmethod
    def set_step(self, step: int, axis: Literal["az", "el"]) -> None:
        """Drive to (maybe device-specific) absolute position."""
        ...

    @abstractmethod
    def set_speed(self, speed: float, axis: Literal["az", "el"]) -> None:
        ...

    @abstractmethod
    def get_step(self, axis: Literal["az", "el"]) -> int:
        """Maybe device-specific absolute position."""
        ...

    @abstractmethod
    def get_speed(self, axis: Literal["az", "el"]) -> u.Quantity:
        ...

    @abstractmethod
    def finalize(self) -> None:
        ...
