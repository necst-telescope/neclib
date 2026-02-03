__all__ = ["TR72W"]

import struct
from typing import Dict
import urllib.request

import astropy.units as u

from ... import get_logger
from ...core.security import busy
from .weather_station_base import WeatherStation


class TR72W(WeatherStation):

    Manufacturer = "TandD"
    Model = "TR72W"

    Identifier = "host"

    def __init__(self) -> None:
        self.logger = get_logger(__name__)
        ip = self.Config.host
        self.url = "http://" + ip + "/B/crrntdata/cdata.txt"

    def _get_data(self) -> Dict[str, float]:
        with busy(self, "busy"):
            try:
                res = urllib.request.urlopen(self.url)
                page = res.read()
                decoded_page = page.decode("shift_jis")
                raw_data = decoded_page.split("\r\n")
                raw_T1 = raw_data[5].split("=")
                raw_T2 = raw_data[6].split("=")
                if raw_T1[1] != "----":
                    temp1 = float(raw_T1[1])
                else:
                    temp1 = 0
                if raw_T2[1] != "----":
                    temp2 = float(raw_T2[1])
                else:
                    temp2 = 0
                return {"temp": temp1, "humid": temp2}
            except struct.error:
                self.logger.warning("Failed to get data from TR73U")
                return {"temp": -273.15, "humid": 0.0}

    def get_temperature(self) -> u.Quantity:
        data = self._get_data()
        data_K = (data["temp"] * u.deg_C).to(u.K, equivalencies=u.temperature())
        return data_K

    def get_humidity(self) -> float:
        data = self._get_data()
        return data["humid"] * 0.01

    def get_pressure(self):
        return 0

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

    def get_pressure(self) -> u.Quantity:
        return 0.0 * u.hPa

    def finalize(self) -> None:
        return

    def close(self) -> None:
        return
