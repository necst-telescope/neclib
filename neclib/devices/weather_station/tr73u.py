__all__ = ["TR73U"]

import astropy.units as u
import ogameasure

from .weather_station_base import WeatherStation


class TR73U(WeatherStation):

    Manufacturer = "TandD"
    Model = "TR73U"

    Identifier = "port"

    def __init__(self) -> None:
        self.ondotori = ogameasure.TandD.tr_73u(self.Config.port)

    def get_temp(self) -> u.Quantity:
        data = self.ondotori.output_current_data()
        data_K = (data["temp"] * u.deg_C).to(u.K, equivalencies=u.temperature())
        return data_K

    def get_humid(self) -> float:
        data = self.ondotori.output_current_data()
        return data["humid"] * 0.01

    def get_press(self) -> u.Quantity:
        data = self.ondotori.output_current_data()
        return data["press"] * u.hPa

    def finalize(self) -> None:
        pass
