from abc import abstractmethod

import astropy.units as u

from ..device_base import DeviceBase


class BiasReader(DeviceBase):

    Manufacturer: str = ""
    Model: str

    @abstractmethod
    def get_data(self) -> u.Quantity:
        ...  # Not yet. None should be changed u.Quantity?
