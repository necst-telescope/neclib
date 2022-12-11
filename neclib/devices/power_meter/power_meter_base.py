from abc import abstractmethod

import astropy.units as u

from ..device_base import DeviceBase


class PowerMeter(DeviceBase):
    @abstractmethod
    def get_power(self) -> u.Quantity:
        ...
