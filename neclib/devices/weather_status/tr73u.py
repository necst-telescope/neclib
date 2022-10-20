__all__ = ["TR73U"]

import astropy.units as u
import ogameasure
from ... import config
from .weather_base import Weather


class Thermometer(Weather):

    Manufacturer = "TandD"
    Model = "TR73U"

    def __init__(self) -> None:
        self.ondotori = ogameasure.TandD.tr_73u(config.antenna_tr73u_port)

    def get_temp(self) -> u.Quantity:
        data = self.ondotori.output_current_data()
        return data["temp" + 273.15] * u.K

    def get_humid(self) -> u.Quantity:
        data = self.ondotori.output_current_data()
        return data["humid"]

    def get_press(self) -> u.Quantity:
        data = self.ondotori.output_current_data()
        return data["press"] * u.hPa

    def finalize(self) -> None:
        pass
