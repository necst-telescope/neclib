from typing import List, Tuple, Union

import numpy as np
import pandas as pd

from astropy import units as u
from astropy.coordinates import Angle
from astropy.time import Time
from matplotlib import pyplot as plt

from ...core import config
from ..convert import CoordCalculator


class PointingList:
    def __init__(self, file_name: str, time: Union[float, str], format: str) -> None:
        self.calc = CoordCalculator(config.location)
        self.now = Time(time, format=format)
        self.obsdatetime = self.now.to_datetime()

    def readlines_file(self, filename: str) -> List[str]:
        with open(filename, mode="r") as file:
            contents = file.readlines()
        return contents

    def to_altaz(self, target: Tuple[u.Quantity, u.Quantity], frame: str, time=0.0):
        if time == 0.0:
            time = self.now
        coord = self.calc.coordinate(
            lon=target[0], lat=target[1], frame=frame, time=time
        )  # TODO: Consider pressure, temperature, relative_humidity, obswl.
        altaz_coord = coord.to_apparent_altaz()
        return altaz_coord

    def _filter(
        self, catalog: pd.DataFrame, magnitude: Tuple[float, float]
    ) -> pd.DataFrame:
        az_range = config.antenna_drive_warning_limit_az
        el_range = config.antenna_drive_warning_limit_el
        filtered = catalog[
            (catalog["az"] > az_range.lower.value)
            & (catalog["az"] < az_range.upper.value)
            & (catalog["el"] > el_range.lower.value)
            & (catalog["el"] < el_range.upper.value)
            & (catalog["multiple"] == " ")
            & (catalog["pmra"] <= 1.0)
            & (catalog["pmdec"] <= 1.0)
            & (catalog["vmag"] >= magnitude[0])
            & (catalog["vmag"] <= magnitude[1])
        ]
        return filtered
