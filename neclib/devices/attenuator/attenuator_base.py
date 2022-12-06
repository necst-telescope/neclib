from abc import abstractmethod

import astropy.units as u

from ..device_base import DeviceBase


class Attenuator(DeviceBase):
    @abstractmethod
    def set_level(self, level_dB: int, ch: int):
        ...

    @abstractmethod
    def get_level(self, ch: int) -> u.Quantity:
        ...
