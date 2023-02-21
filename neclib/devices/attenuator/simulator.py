from collections import defaultdict

import astropy.units as u

from ...core.units import dBm
from .attenuator_base import Attenuator


class AttenuatorSimulator(Attenuator):
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
