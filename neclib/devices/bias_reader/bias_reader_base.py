from abc import abstractmethod

import astropy.units as u

from ..device_base import DeviceBase


class BiasReader(DeviceBase):

    Manufacturer: str = ""
    Model: str

    @abstractmethod
    def get_bias_voltage(self, ch) -> u.Quantity:
        ...

    @abstractmethod
    def get_bias_current(self, ch) -> u.Quantity:
        ...

    @abstractmethod
    def finalize(self) -> None:
        ...
