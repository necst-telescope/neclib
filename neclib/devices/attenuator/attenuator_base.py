from abc import abstractmethod

import astropy.units as u

from ..device_base import DeviceBase


class Attenuator(DeviceBase):
    @abstractmethod
    def set_loss(self, dB: int, id: str):
        ...

    @abstractmethod
    def get_loss(self, id: str) -> u.Quantity:
        ...
