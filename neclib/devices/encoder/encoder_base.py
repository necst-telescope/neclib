from abc import ABC, abstractmethod

import astropy.units as u


class Encoder(ABC):

    Manufacturer: str = ""
    Model: str

    @abstractmethod
    def get_reading(self) -> u.Quantity:
        ...

    @abstractmethod
    def finalize(self) -> None:
        ...
