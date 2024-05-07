from collections import defaultdict

import astropy.units as u

from ...core.units import dBm
from .attenuator_base import CurrentAttenuator, NetworkAttenuator


class NetworkAttenuatorSimulator(NetworkAttenuator):
    Manufacturer: str = ""
    Model: str = ""
    Identifier = ""
    is_simulator = True

    def __init__(self) -> None:
        self.loss = defaultdict(lambda: 0)

    def set_loss(self, dB: int, id: str):
        self.loss[id] = dB

    def get_loss(self, id: str) -> u.Quantity:
        return self.loss[id] * dBm

    def finalize(self) -> None:
        pass


class CurrentAttenuatorSimulator(CurrentAttenuator):
    Manufacturer: str = ""
    Model: str = ""
    Identifier = ""
    is_simulator = True

    def __init__(self) -> None: ...

    def get_outputrange(self, id: int) -> dict: ...

    def set_outputrange(self, id: int, outputrange: str): ...

    def output_current(self, id: int, current: float): ...

    def finalize(self): ...
