from abc import abstractmethod

import astropy.units as u

from ..device_base import DeviceBase


class NetworkAttenuator(DeviceBase):
    @abstractmethod
    def set_loss(self, dB: int, id: str): ...

    @abstractmethod
    def get_loss(self, id: str) -> u.Quantity: ...

    @abstractmethod
    def close(self) -> None: ...


class CurrentAttenuator(DeviceBase):
    @abstractmethod
    def get_outputrange(self, ch: int) -> dict: ...

    @abstractmethod
    def set_outputrange(self, id: int, outputrange: str): ...

    @abstractmethod
    def set_current(self, id: str, mA: float): ...

    @abstractmethod
    def apply_current(self): ...

    @abstractmethod
    def finalize(self): ...

    @abstractmethod
    def close(self): ...
