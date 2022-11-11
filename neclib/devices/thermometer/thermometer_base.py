from abc import ABC, abstractmethod  # noaq:F401

import astropy.units as u


class Thermometer(ABC):

    Manufacturer: str = ""
    Model: str

    @abstractmethod
    def get_temp(self) -> u.Quantity:
        ...

    @abstractmethod
    def finalize(self) -> None:
        ...
