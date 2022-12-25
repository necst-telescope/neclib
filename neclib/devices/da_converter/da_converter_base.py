from abc import abstractmethod

from ..device_base import DeviceBase


class DAConverter(DeviceBase):

    Manufacturer: str = ""
    Model: str

    @abstractmethod
    def set_voltage(self, mV: float, id: str) -> None:
        ...

    @abstractmethod
    def apply_voltage(self) -> None:
        ...

    @abstractmethod
    def finalize(self) -> None:
        ...
