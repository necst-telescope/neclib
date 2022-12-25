from abc import abstractmethod

import astropy.units as u

from ..device_base import DeviceBase


class ADConverter(DeviceBase):

    Manufacturer: str = ""
    Model: str

    @abstractmethod
    def get_voltage(self, id: str) -> u.Quantity:
        ...

    @abstractmethod
    def get_current(self, id: str) -> u.Quantity:
        ...

    @abstractmethod
    def finalize(self) -> None:
        ...
