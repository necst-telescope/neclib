__all__ = ["TR702W"]

from typing import Dict

import astropy.units as u
import ogameasure

from ... import get_logger
from ...core.security import busy
from .weather_station_base import WeatherStation


class TR702W(WeatherStation):
    Manufacturer = "TandD"
    Model = "TR702W"
    Identifier = "host"

    def __init__(self) -> None:
        self.logger = get_logger(__name__)
        # tr72w.pyはHTTP通信だったためIPのみ必要だったが、tr702wではポート番号とパスワードが必要である。TCPソケットで通信するため、URLを定義する必要がない。
        try:
            ip = self.Config.host
            port = getattr(self.Config, "port", 62500)
            password = getattr(self.Config, "password", "password")
        except Exception as e:
            self.logger.error(f"failed to get config from TR702W: {e}")
        self.com = ogameasure.ethernet(ip, port)
        self.ondotori = ogameasure.TandD.tr_702w(self.com, password=password)

    def _get_data(self) -> Dict[str, float]:
        with busy(self, "busy"):
            try:
                data = self.ondotori.output_current_data()
                if data is None:
                    self.logger.warning(" sensor error or empty data.")
                    return {"temp": 0.0, "humid": 0.0}
                return {"temp": data["temp"], "humid": data["humid"]}
            except Exception as e:
                self.logger.warning(f"failed to get data from TR702W: {e}")
                try:
                    self.ondotori._reconnect()
                except Exception:
                    pass
                return {"temp": 0.0, "humid": 0.0}

    def get_temperature(self) -> u.Quantity:
        data = self._get_data()
        data_K = (data["temp"] * u.deg_C).to(u.K, equivalencies=u.temperature())
        return data_K

    def get_humidity(self) -> float:
        data = self._get_data()
        # ogameasureでは湿度を0~100で表示するため、0.01をかける
        return data["humid"] * 0.01

    def get_in_temperature(self) -> u.Quantity:
        return 0 * u.K

    def get_in_humidity(self) -> float:
        return 0

    def get_wind_speed(self) -> u.Quantity:
        return 0 * u.m / u.s

    def get_wind_direction(self) -> u.Quantity:
        return 0 * u.deg

    def get_rain_rate(self) -> float:
        return 0

    def get_pressure(self) -> u.Quantity:
        return 0.0 * u.hPa

    def finalize(self) -> None:
        self.close()

    def close(self) -> None:
        try:
            if hasattr(self, "device"):
                self.ondotori.close()
        except Exception as e:
            self.logger.warning(f"Error while closing TR702W connection: {e}")
