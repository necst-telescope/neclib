from typing import List, Tuple, Union

import numpy as np
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
        # TODO: Implement.
        ...

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

    def _filter(self, catalog: List[str], magnitude: float) -> List[str]:
        # TODO: Implement.
        ...

    def sort(
        self, catalog_file: str, magnitude: Tuple[float, float]
    ):  # HACK: Now almost copied from v3.
        # from operator import itemgetter
        def itemgetter(item):
            return lambda x: x[item]

        catalog_raw = self.readlines_file(filename=catalog_file)
        # catalog = self._catalog_to_pandas(catalog_raw=catalog_raw)
        az_range = config.antenna_drive_warning_limit_az
        el_range = config.antenna_drive_warning_limit_el
        data = []
        for line in catalog_raw:
            try:
                ra2000 = (
                    float(line[75:77])
                    + float(line[77:79]) / 60.0  # arcmin
                    + float(line[79:83]) / 3600.0  # arcsec
                ) * u.hourangle
                ra2000 = ra2000.to(u.deg)
                dec2000 = (
                    float(line[84:86]) * u.deg
                    + float(line[86:88]) * u.arcmin
                    + float(line[88:90]) * u.arcsec
                )
                if line[83:84] == "-":
                    dec2000 = -dec2000
                multiple = line[43:44]
                vmag = float(line[103:107])
                pmra = float(line[149:154])
                pmdec = float(line[154:160])
                altaz = self.to_altaz(target=(ra2000, dec2000), frame="fk5")
                # print(f"az: {altaz.az}, el: {altaz.alt}")

                if (
                    altaz.az in az_range
                    and altaz.alt in el_range
                    and multiple == " "
                    and vmag >= magnitude[0]
                    and vmag <= magnitude[1]
                    and pmra <= 1.0  # parameterized from v3
                    and pmdec <= 1.0  # parameterized from v3
                ):
                    data.append(
                        [line[7:14], ra2000, dec2000, pmra, pmdec, altaz.az, altaz.alt]
                    )
            except Exception:
                pass

        sdata = np.array(sorted(data, key=itemgetter(5)))  # sort by az
        # print(f"sdata: {sdata}")
        tmp = sdata[:, 5].astype(np.float64)

        # print("sdata", tmp)
        ddata = np.array([]).reshape(0, 7)
        elflag = 0
        azint = 100 * u.deg
        # print(f"az_range[0]: {az_range.lower.value}")
        # print(f"az_range[1]: {az_range.upper.value}")
        for azaz in np.arange(az_range.lower.value, az_range.upper.value, azint.value):
            # print("azmin, azmax, azint:", az_range[0], az_range[1], azint)
            # print(f"min: {min(azaz, azaz + azint.value)}")
            # print(f"max: {max(azaz, azaz + azint.value)}")
            ind = np.where(
                (tmp > min(azaz, azaz + azint.value))
                & (tmp < max(azaz, azaz + azint.value))
            )
            # print("ind", ind)
            # print("len ind", len(ind))
            dum = sdata[ind[0], :]
            ind2 = np.argsort(dum[:, 6])
            if elflag == 0:
                elflag = 1
            else:
                ind2 = ind2[::-1]
                elflag = 0
            ddata = np.append(ddata, dum[ind2, :], axis=0)
            continue

        # x = np.round(ddata[:, 5].astype(np.float64), 2)
        # y = np.round(ddata[:, 6].astype(np.float64), 2)
        # x = ddata[:, 5]  # .astype(np.float64)
        # y = ddata[:, 6]  # .astype(np.float64)
        # print(f"x: {x}")
        # print(f"y: {y}")
        x = ddata[:, 5].astype(np.float64)
        y = ddata[:, 6].astype(np.float64)
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
