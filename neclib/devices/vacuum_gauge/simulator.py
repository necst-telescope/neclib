import astropy.units as u

from ...core.math import Random
from .vacuum_gauge_base import VacuumGauge


class VacuumGaugeSimulator(VacuumGauge):
    Manufacturer: str = ""
    Model: str = ""
    Identifier = ""
    is_simulator = True

    def __init__(self) -> None:
        self._rand = Random().walk(1e-8, 1e-9, -1)

    def get_pressure(self) -> u.Quantity:
        return 1e-8 * u.Torr  # type: ignore

    def finalize(self) -> None:
        pass
