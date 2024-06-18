from abc import abstractmethod

import astropy.units as u

from ..device_base import DeviceBase


class Membrane(DeviceBase):

    Manufacturer: str = ""
    Model: str

    @abstractmethod
    def memb_open(self) -> None:
        """Open membrane."""
        ...

    @abstractmethod
    def memb_close(self) -> None:
        """Close membrane."""
        ...
