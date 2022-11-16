from abc import abstractmethod
from typing import Literal

import astropy.units as u

from ..device_base import DeviceBase


class Encoder(DeviceBase):

    # Manufacturer: str = ""
    # Model: str

    @abstractmethod
    def get_reading(self, axis: Literal["az", "el"]) -> u.Quantity:
        ...

    @abstractmethod
    def finalize(self) -> None:
        ...
