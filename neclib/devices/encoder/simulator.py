import astropy.units as u

from ...core.math import Random
from .encoder_base import Encoder


class EncoderSimulator(Encoder):
    Manufacturer: str = ""
    Model: str = ""
    Identifier = ""
    is_simulator = True

    def __init__(self) -> None:
        self._rand = Random().walk(-16, 0.1, -1)

    def get_reading(self) -> u.Quantity:
        raise NotImplementedError

    def finalize(self) -> None:
        pass
