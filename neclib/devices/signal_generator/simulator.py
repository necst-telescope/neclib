from typing import Union

import astropy.units as u

from .signal_generator_base import SignalGenerator


class SignalGeneratorSimulator(SignalGenerator):
    Manufacturer: str = ""
    Model: str = ""
    Identifier = ""
    is_simulator = True

    def __init__(self) -> None:
        self.freq = 0
        self.power = 0
        self.output_status = False

    def set_freq(self, GHz: Union[int, float]) -> None:
        self.freq = GHz

    def set_power(self, dBm: Union[int, float]) -> None:
        self.power = dBm

    def get_freq(self) -> u.Quantity:
        return self.freq * u.GHz  # type: ignore

    def get_power(self) -> u.Quantity:
        return self.power * u.dBm  # type: ignore

    def start_output(self) -> None:
        self.output_status = True

    def stop_output(self) -> None:
        self.output_status = False

    def get_output_status(self) -> bool:
        return self.output_status

    def finalize(self) -> None:
        pass
