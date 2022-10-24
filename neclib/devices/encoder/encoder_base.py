from abc import ABC, abstractmethod
from typing import Literal

import astropy.units as u


class Encoder(ABC):

    Manufacturer: str = ""
    Model: str

    @abstractmethod
    def get_reading(self, axis: Literal["az", "el"]) -> u.Quantity:
        ...

    @abstractmethod
    def finalize(self) -> None:
        ...
