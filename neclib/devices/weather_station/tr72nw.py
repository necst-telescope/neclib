__all__ = ["TR72NW"]

from typing import Dict

import astropy.units as u
import ogameasure

from ... import get_logger
from ...core.security import busy
from .weather_station_base import WeatherStation


class TR72NW(WeatherStation):
    Manufacturer = "TandD"
    Model = "TR-72NW"

    Identifier = "host"

    def __init__(self) -> None:
        self.logger = get_logger(__name__)
        # config.tomlから設定を読み込む
        ip = self.Config.host
        port = getattr(self.Config, "port", 57172)
        # シリアル番号の取得
        raw_serial = getattr(self.Config, "serial_no", None)
        # 16進数文字列を整数に変換
        if isinstance(raw_serial, str):
            serial_no = int(raw_serial, 16)
        else:
            serial_no = int(raw_serial)

        self.com = ogameasure.ethernet(ip, port)
        self.dev = ogameasure.TandD.tr_72nw(self.com, serial_no=serial_no)

    def _get_data(self) -> Dict[str, float]:
        with busy(self, "busy"):
            try:
                data = self.dev.output_current_data()
                if data is None:
                    self.logger.warning("sensor error or empty data.")
                    return {"temp": 0.0, "humid": 0.0}
                return {"temp": data["temp"], "humid": data["humid"]}
            except Exception as e:
                self.logger.warning(f"failed to get data from TR72NW: {e}")
                return {"temp": 0.0, "humid": 0.0}

    def get_temperature(self) -> u.Quantity:
        data = self._get_data()
        data_K = (data["temp"] * u.deg_C).to(u.K, equivalencies=u.temperature())
        return data_K

    def get_humidity(self) -> float:
        data = self._get_data()
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
                self.dev.close()
        except Exception as e:
            self.logger.warning(f"Error while closing TR72NW connection: {e}")
