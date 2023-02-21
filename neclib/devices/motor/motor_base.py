from abc import abstractmethod

import astropy.units as u

from ..device_base import DeviceBase


class Motor(DeviceBase):

    Manufacturer: str = ""
    Model: str

    @abstractmethod
    def set_step(self, step: int, axis: str) -> None:
        """Drive to (maybe device-specific) absolute position."""
        ...

    @abstractmethod
    def set_speed(self, speed: float, axis: str) -> None:
        ...

    @abstractmethod
    def get_step(self, axis: str) -> int:
        """Maybe device-specific absolute position."""
        ...

    @abstractmethod
    def get_speed(self, axis: str) -> u.Quantity:
        ...

    @abstractmethod
    def finalize(self) -> None:
        ...
