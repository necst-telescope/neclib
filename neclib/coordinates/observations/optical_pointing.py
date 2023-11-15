from typing import List, Tuple, Union

import numpy as np
import pandas as pd

from astropy import units as u
from astropy.time import Time
from matplotlib import pyplot as plt

from ...core import config
from ..convert import CoordCalculator


class OpticalPointingSpec:
    def __init__(self, time: Union[float, str], format: str) -> None:
        self.cal = CoordCalculator(config.location)
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
                ra = (
                    float(line[75:77]) * u.hourangle
                    + float(line[77:79]) * u.arcmin
                    + float(line[79:83]) * u.arcsec
                ).to(u.deg)
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
        # if time == 0.0:
        #     time = self.now
        # location = config.location
        # altaz = AltAz(obstime=time, location=location)
        # coord = SkyCoord(lon=target[0], lat=target[1], frame=frame)
        # altaz_coord = coord.transform_to(frame=altaz)
        if time == 0.0:
            time = self.now
        coord = self.cal.coordinate(
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

    def sort(
        self, catalog_file: str, magnitude: Tuple[float, float]
    ):  # HACK: Now almost copied from v3.
        az_range = config.antenna_drive_warning_limit_az

        catalog_raw = self.readlines_file(filename=catalog_file)
        catalog = self._catalog_to_pandas(catalog_raw=catalog_raw)
        catalog = self._filter(catalog, magnitude)

        sdata = catalog.sort_values("az", ignore_index=True)  # sort by az
        # print(f"sdata: {sdata}")

        # print("sdata", tmp)

        ddata = pd.DataFrame(index=[], columns=sdata.columns)
        elflag = 0
        azint = 100 * u.deg
        # print(f"az_range[0]: {az_range.lower.value}")
        # print(f"az_range[1]: {az_range.upper.value}")
        for azaz in np.arange(az_range.lower.value, az_range.upper.value, azint.value):
            # print("azmin, azmax, azint:", az_range[0], az_range[1], azint)
            # print(f"min: {min(azaz, azaz + azint.value)}")
            # print(f"max: {max(azaz, azaz + azint.value)}")

            ind = sdata[
                (sdata["az"] >= min(azaz, azaz + azint.value))
                & (sdata["az"] <= max(azaz, azaz + azint.value))
            ]

            # print("ind", ind)
            # print("len ind", len(ind))

            ind2 = ind.sort_values("el", ignore_index=True)
            if elflag == 0:
                elflag = 1
            else:
                ind2 = ind2[::-1]
                elflag = 0
            ddata = ddata.append(ind2)
            continue
        ddata = ddata.reset_index(drop=True)
        # x = np.round(ddata[:, 5].astype(np.float64), 2)
        # y = np.round(ddata[:, 6].astype(np.float64), 2)
        # x = ddata[:, 5]  # .astype(np.float64)
        # y = ddata[:, 6]  # .astype(np.float64)
        # print(f"x: {x}")
        # print(f"y: {y}")

        x = ddata["az"].values.astype(np.float64)
        y = ddata["el"].values.astype(np.float64)
        # print(f"x_astype: {x}")
        # print(f"y_astype: {y}")
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

        # print(f"ddata: {ddata}")
        return ddata
