import astropy.units as u

from ...core.math import Random
from .thermometer_base import Thermometer


class ThermometerSimulator(Thermometer):
    Manufacturer: str = ""
    Model: str = ""
    Identifier = ""
    is_simulator = True

    def __init__(self) -> None:
        self._rand = Random().walk(4, 0.1, -1)

    def get_temp(self, id: str) -> u.Quantity:
        return next(self._rand) * u.K

    def finalize(self) -> None:
        pass
