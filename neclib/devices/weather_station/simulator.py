import astropy.units as u

from ...core.math import Random
from .weather_station_base import WeatherStation


class WeatherStationSimulator(WeatherStation):

    Manufacturer: str = ""
    Model: str = ""
    Identifier = ""
    is_simulator = True

    def __init__(self) -> None:
        self._random_temp = Random().walk(15, 0.1, -10)
        self._random_hum = Random(limits=(0, 1)).walk(0.3, 0.01, -7)
        self._random_pres = Random().walk(850, 0.1, -7)

    def get_temperature(self) -> u.Quantity:
        return next(self._random_temp) * u.deg_C

    def get_humidity(self) -> float:
        return next(self._random_hum)

    def get_pressure(self) -> u.Quantity:
        return next(self._random_pres) * u.hPa  # type: ignore

    def finalize(self) -> None:
        pass
