__all__ = ["TR73U"]

import astropy.units as u

import ogameasure

from ... import config
from .weather_base import Weather


class TR73U(Weather):

    Manufacturer = "TandD"
    Model = "TR73U"

    def __init__(self) -> None:
        self.ondotori = ogameasure.TandD.tr_73u(config.antenna_tr73u_port)

    def get_temp(self) -> u.Quantity:
        data = self.ondotori.output_current_data()
        data_K = (data["temp"] * u.deg_C).to(u.K, equivalencies=u.temperature())
        return data_K

    def get_humid(self) -> float:
        data = self.ondotori.output_current_data() * 0.01
        return data["humid"]

    def get_press(self) -> u.Quantity:
        data = self.ondotori.output_current_data()
        return data["press"] * u.hPa

    def finalize(self) -> None:
        pass
