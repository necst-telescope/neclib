from abc import abstractmethod

from ..device_base import DeviceBase


class BiasSetter(DeviceBase):

    Manufacturer: str = ""
    Model: str

    @abstractmethod
    def set_voltage(self, voltage_mV: float, ch: int) -> None:
        ...

    @abstractmethod
    def output_voltage(self) -> None:
        ...

    @abstractmethod
    def finalize(self) -> None:
        ...
