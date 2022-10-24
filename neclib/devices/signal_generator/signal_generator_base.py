from abc import ABC, abstractmethod


class SignalGenerator(ABC):

    Manufacturer: str = ""
    Model: str

    @abstractmethod
    def set_freq(self, freq_GHz) -> None:
        ...

    @abstractmethod
    def set_power(self, power_dBm) -> None:
        ...

    @abstractmethod
    def get_freq(self) -> float:
        ...

    @abstractmethod
    def get_power(self) -> float:
        ...

    @abstractmethod
    def set_onoff(self, q) -> None:
        ...
