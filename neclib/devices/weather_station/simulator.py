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
        return (next(self._random_temp) + 273.15) * u.K

    def get_humidity(self) -> float:
        return next(self._random_hum)

    def get_pressure(self) -> u.Quantity:
        return next(self._random_pres) * u.hPa  # type: ignore

    def get_in_temperature():
        return 0
    
    def get_in_humidity():
        return 0
    
    def get_wind_speed():
        return 0
    
    def get_wind_direction():
        return 0
    
    def get_rain_rate():
        return 0

    def finalize(self) -> None:
        pass

    def close(seld) -> None:
        pass
