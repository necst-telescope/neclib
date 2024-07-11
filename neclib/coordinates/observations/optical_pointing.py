from typing import List, Tuple, Union

import numpy as np
import pandas as pd

from astropy import units as u
from astropy.coordinates import Angle
from astropy.time import Time
from matplotlib import pyplot as plt

from ...core import config
from ..convert import CoordCalculator


class OpticalPointingSpec:
    def __init__(self, time: Union[float, str], format: str) -> None:
        self.calc = CoordCalculator(config.location)
        self.now = Time(time, format=format)
        self.obsdatetime = self.now.to_datetime()

    def readlines_file(self, filename: str) -> List[str]:
        with open(filename, mode="r") as file:
            contents = file.readlines()
        return contents

    def _catalog_to_pandas(self, catalog_raw: List[str]):
        name_data = []
        ra_data = []
        dec_data = []
        multiple_data = []
        vmag_data = []
        pmra_data = []
        pmdec_data = []
        az_data = []
        el_data = []
        for line in catalog_raw:
            try:
                name = line[7:14]

                ra_raw = line[75:77] + "h" + line[77:79] + "m" + line[79:83] + "s"
                ra = Angle(ra_raw).to(u.deg)

                dec = (
                    float(line[84:86]) * u.deg
                    + float(line[86:88]) * u.arcmin
                    + float(line[88:90]) * u.arcsec
                ).to(u.deg)
                if line[83:84] == "-":
                    dec = -dec
                altaz = self.to_altaz(target=(ra, dec), frame="fk5")
                multiple = line[43:44]
                vmag = float(line[103:107])
                pmra = float(line[149:154])
                pmdec = float(line[154:160])
            except Exception:
                pass
            ra_data.append(ra.value)
            dec_data.append(dec.value)
            multiple_data.append(multiple)
            vmag_data.append(vmag)
            pmra_data.append(pmra)
            pmdec_data.append(pmdec)
            name_data.append(name)
            az_data.append(altaz.az.value)
            el_data.append(altaz.alt.value)
        data = pd.DataFrame(
            {
                "name": name_data,
                "ra": ra_data,
                "dec": dec_data,
                "pmra": pmra_data,
                "pmdec": pmdec_data,
                "az": az_data,
                "el": el_data,
                "vmag": vmag_data,
                "multiple": multiple_data,
            }
        )
        return data

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

    def sort(self, catalog_file: str, magnitude: Tuple[float, float]):
        az_range = config.antenna_drive_warning_limit_az

        catalog_raw = self.readlines_file(filename=catalog_file)
        catalog = self._catalog_to_pandas(catalog_raw=catalog_raw)
        catalog = self._filter(catalog, magnitude)

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
        el_speed = config.antenna.max_speed_el.value
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
