from typing import List, Tuple, Union

import numpy as np
import pandas as pd

from astropy import units as u
from astropy.coordinates import Angle
from astropy.time import Time
from matplotlib import pyplot as plt

from .pointing_list import PointingList
from ...core import config
from ..convert import CoordCalculator


class OpticalPointingSpec:
    def __init__(self, time: Union[float, str], format: str) -> None:
        self.calc = CoordCalculator(config.location)
        self.now = Time(time, format=format)
        self.obsdatetime = self.now.to_datetime()

    def make_sorted_table(self, catalog_file: str, magnitude: Tuple[float, float]):
        az_range = config.antenna_drive_warning_limit_az

        pointing_list = PointingList(file_name=catalog_file)

        catalog = pointing_list.filter(magnitude)

        sdata = catalog.sort_values("az", ignore_index=True)  # sort by az

        ddata = pd.DataFrame(index=[], columns=sdata.columns)
        elflag = 0
        azint = 100 * u.deg

        for azaz in np.arange(az_range.lower.value, az_range.upper.value, azint.value):
            ind = sdata[
                (sdata["az"] >= min(azaz, azaz + azint.value))
                & (sdata["az"] <= max(azaz, azaz + azint.value))
            ]

            ind2 = ind.sort_values("el", ignore_index=True)
            if elflag == 0:
                elflag = 1
            else:
                ind2 = ind2[::-1]
                elflag = 0
            ddata = ddata.append(ind2)
            continue
        ddata = ddata.reset_index(drop=True)

        x = ddata["az"].values.astype(np.float64)
        y = ddata["el"].values.astype(np.float64)

        show_graph = True
        if show_graph is True:
            plt.figure()
            plt.plot(x, y)
            plt.grid()
            plt.xlabel("Az")
            plt.ylabel("El")
            plt.title(
                "Optical Pointing Locus\n"
                f"obstime = {str(self.obsdatetime)}\n"
                f"star num = {str(len(ddata))}"
            )
            plt.show()

        return ddata

    def estimate_time(self, sorted_data: pd.DataFrame):
        az_speed = config.antenna.max_speed_az.value
        el_speed = config.antenna.max_speed_el.valueopt
        time_list = []
        for i in range(len(sorted_data) - 1):
            delta_az = sorted_data["az"][i + 1] - sorted_data["az"][i]
            delta_el = sorted_data["el"][i + 1] - sorted_data["el"][i]
            if delta_az > delta_el:
                t = delta_az / az_speed
            elif delta_az < delta_el:
                t = delta_el / el_speed
            t = t + 30.0
            time_list.append(t)

        t_tot = sum(time_list)
        return t_tot
