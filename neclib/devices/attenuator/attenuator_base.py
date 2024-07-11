from abc import abstractmethod

import astropy.units as u

from ..device_base import DeviceBase


class NetworkAttenuator(DeviceBase):
    @abstractmethod
    def set_loss(self, dB: int, id: str): ...

    @abstractmethod
    def get_loss(self, id: str) -> u.Quantity: ...


class CurrentAttenuator(DeviceBase):
    @abstractmethod
    def get_outputrange(self, ch: int) -> dict: ...

    @abstractmethod
    def set_outputrange(self, ch: int, outputrange: str): ...

    @abstractmethod
    def output_current(self, ch: int, current: float): ...

    @abstractmethod
    def finalize(self): ...
