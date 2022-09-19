from abc import ABC, abstractmethod

import astropy.units as u


class Encoder(ABC):

    Manufacturer: str = ""
    Model: str

    @abstractmethod
    def get_reading(self) -> u.Quantity:
        ...
