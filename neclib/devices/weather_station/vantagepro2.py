__all__ = ["VantagePro2"]

from weather import units
import weather.stations.davis as weatherlink

import astropy.units as u

from .weather_station_base import WeatherStation


class VantagePro2(WeatherStation):
    Manufacturer = "Davis"
    Model = "VantagePro2"

    Identifier = "port"

    def __init__(self) -> None:
        self.vantage = weatherlink.VantagePro(self.Config.port)

    def _get_data(self) -> dict:
        self.vantage._cmd("CLRLOG")

        ret = self.vantage.parse()

        if ret["EOL"] == b"\n\r":
            return ret

        else:
            print("Can not access weather station")

    def get_temperature(self) -> u.Quantity:
        data = self._get_data()
        data_K = units.fahrenheit_to_kelvin(data["TempOut"]) * u.K
        return data_K

    def get_in_temperature(self) -> u.Quantity:
        data = self._get_data()
        data_K = units.fahrenheit_to_kelvin(data["TempIn"]) * u.K
        return data_K

    def get_humidity(self) -> float:
        data = self._get_data()
        return data["HumOut"] * 0.01

    def get_in_humidity(self) -> float:
        data = self._get_data()
        return data["HumIn"] * 0.01

    def get_pressure(self) -> u.Quantity:
        data = self._get_data()
        data_press = units.incConv_to_Pa(data["Pressure"]) * 10 * u.hPa
        return data_press

    def get_wind_speed(self) -> float:
        data = self._get_data()
        data_WindSpeed = units.mph_to_m_sec(data["WindSpeed"]) * u.m / u.second
        return data_WindSpeed

    def get_wind_direction(self) -> u.Quantity:
        data = self._get_data()
        return data["WindDir"] * u.deg

    def get_rain_rate(self) -> float:
        data = self._get_data()
        return data["RainRate"]

    def finalize(self) -> None:
        self.vantage.__del__()
