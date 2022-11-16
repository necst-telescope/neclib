from abc import abstractmethod

import astropy.units as u

from ..device_base import DeviceBase


class Weather(DeviceBase):

    Manufacturer: str = ""
    Model: str

    @abstractmethod
    def get_temp(self) -> u.Quantity:
        ...

    @abstractmethod
    def get_humid(self) -> float:
        ...

    @abstractmethod
    def get_press(self) -> u.Quantity:
        ...

    @abstractmethod
    def finalize(self) -> None:
        ...
