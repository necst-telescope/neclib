from abc import abstractmethod

import astropy.units as u

from ..device_base import DeviceBase


class VacuumGauge(DeviceBase):
    @abstractmethod
    def get_pressure(self) -> u.Quantity:
        ...
