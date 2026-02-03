from abc import abstractmethod

import astropy.units as u

from ..device_base import DeviceBase


class ADConverter(DeviceBase):

    Manufacturer: str = ""
    Model: str

    @abstractmethod
    def get_all(self, target: str) -> dict: ...

    @abstractmethod
    def get_from_id(self, id: str) -> u.Quantity: ...

    @abstractmethod
    def finalize(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...
