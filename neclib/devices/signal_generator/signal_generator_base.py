from abc import abstractmethod
import astropy.units as u

from ..device_base import DeviceBase


class SignalGenerator(DeviceBase):

    Manufacturer: str = ""
    Model: str

    @abstractmethod
    def set_freq(self, freq_GHz) -> None:
        ...

    @abstractmethod
    def set_power(self, power_dBm) -> None:
        ...

    @abstractmethod
    def get_freq(self) -> u.Quantity:
        ...

    @abstractmethod
    def get_power(self) -> u.Quantity:
        ...

    @abstractmethod
    def start_output(self) -> None:
        ...

    @abstractmethod
    def stop_output(self) -> None:
        ...

    @abstractmethod
    def get_output_status(self) -> bool:
        ...

    @abstractmethod
    def finalize(self) -> None:
        ...
