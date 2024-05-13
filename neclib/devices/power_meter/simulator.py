import astropy.units as u

from ...core.math import Random
from ...core.units import dBm
from .power_meter_base import PowerMeter


class PowerMeterSimulator(PowerMeter):
    Manufacturer: str = ""
    Model: str = ""
    Identifier = ""
    is_simulator = True

    def __init__(self) -> None:
        self._rand = Random().walk(-16, 0.1, -1)

    def get_power(self) -> u.Quantity:
        return next(self._rand) * dBm

    def finalize(self) -> None:
        pass
