from abc import ABC, abstractmethod

import astropy.units as u
from numpy import float64


class Weather(ABC):

    Manufacturer: str = ""
    Model: str

    @abstractmethod
    def get_temp(self) -> u.Quantity:
        ...

    @abstractmethod
    def get_humid(self) -> float64:
        ...

    @abstractmethod
    def get_press(self) -> u.Quantity:
        ...

    @abstractmethod
    def finalize(self) -> None:
        ...
