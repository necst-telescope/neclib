from abc import abstractmethod

import astropy.units as u

from ..device_base import DeviceBase


class BiasReader(DeviceBase):

    Manufacturer: str = ""
    Model: str

    @abstractmethod
    def get_voltage(self, ch) -> u.Quantity:
        ...

    @abstractmethod
    def get_current(self, ch) -> u.Quantity:
        ...
