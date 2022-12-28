from abc import abstractmethod
from typing import Union

import astropy.units as u

from ..device_base import DeviceBase


class SignalGenerator(DeviceBase):

    Manufacturer: str = ""
    Model: str

    @abstractmethod
    def set_freq(self, GHz: Union[int, float]) -> None:
        ...

    @abstractmethod
    def set_power(self, dBm: Union[int, float]) -> None:
        ...

    @abstractmethod
    def get_freq(self) -> u.Quantity:
        ...

    @abstractmethod
    def get_power(self) -> u.Quantity:
        ...

    @abstractmethod
    def start_output(self) -> None:
        ...

    @abstractmethod
    def stop_output(self) -> None:
        ...

    @abstractmethod
    def get_output_status(self) -> bool:
        ...

    @abstractmethod
    def finalize(self) -> None:
        ...
