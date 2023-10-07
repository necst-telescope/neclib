from typing import List, Tuple, Union

import numpy as np
from astropy.time import Time
from matplotlib import pyplot as plt

from neclib import ValueRange, config
from neclib.coordinates.convert import CoordCalculator


class OpticalPointingSpec:
    def __init__(self, time: Union[float, str], format: str):
        self.cal = CoordCalculator(config.location)
        self.now = Time(time, format=format)

    def readlines_file(self, filename: str) -> List[str]:
        with open(filename, mode="r") as file:
            contents = file.readlines()
        return contents

    def _catalog_to_pandas(self, catalog_raw: List[str]):
        # TODO: Implement.
        ...

    def to_altaz(self, target: Tuple[float, float], frame: str, unit: str, time=0.0):
        if time == 0.0:
            time = self.now
        coord = self.cal.coordinate(
            lon=target[0], lat=target[1], frame=frame, time=time, unit=unit
        )
        altaz_coord = coord.to_apparent_altaz()
        return altaz_coord

    def _filter(self, catalog: List[str], magnitude: float) -> List[str]:
        # TODO: Implement.
        ...

    def sort(
        self, catalog_file: str, magnitude: float
    ):  # HACK: Now almost copied from v3.
        # from operator import itemgetter
        def itemgetter(item):
            return lambda x: x[item]

        catalog_raw = self.readlines_file(filename=catalog_file)
        # catalog = self._catalog_to_pandas(catalog_raw=catalog_raw)
        az_range = ValueRange(
            config.antenna_drive_warning_limit_az
        )  # ValueRange オブジェクト。正直critical limitでもいいんだけどルート決めから観測まで時間差が若干あることを加味してwarning？
        el_range = ValueRange(config.antenna_drive_warning_limit_el)
        data = []
        for line in catalog_raw:
            # ターゲットを`to_altaz`に渡して変換
            ra2000 = (
                float(line[75:77])  # deg
                + float(line[77:79]) / 60.0  # arcmin
                + float(line[79:83]) / 3600.0  # arcsec
            )
            dec2000 = (
                float(line[84:86])  # deg
                + float(line[86:88]) / 60.0  # arcmin
                + float(line[88:90]) / 3600.0  # arcsec
            )
            if line[83:84] == "-":
                dec2000 = -dec2000
            multiple = line[43:44]
            vmag = float(line[103:107])
            pmra = float(line[149:154])
            pmdec = float(line[154:160])
            altaz = self.to_altaz(target=(ra2000, dec2000), frame="fk5", unit="deg")

            if (
                altaz.az in az_range
                and altaz.el in el_range
                and multiple == " "
                and vmag <= magnitude
                and pmra <= 1.0  # parameterized from v3
                and pmdec <= 1.0  # parameterized from v3
            ):
                data.append(
                    [line[7:14], ra2000, dec2000, pmra, pmdec, altaz.az, altaz.alt]
                )  # 天体番号、RADec、AltAz、pmRADec(?), vmagを追記。

        # Azでソート
        sdata = np.array(sorted(data, key=itemgetter(5)))  # sort by az
        tmp = sdata[:, 5].astype(np.float64)

        # Az30deg毎に区切ってElソート。毎回昇順と降順を切り替える。`sdata`
        print("sdata", tmp)
        ddata = np.array([]).reshape(0, 7)
        elflag = 0
        azint = 40
        for azaz in np.arange(az_range[0], az_range[1], azint):
            print("azmin, azmax, azint:", az_range[0], az_range[1], azint)
            ind = np.where(
                (tmp > min(azaz, azaz + azint)) and (tmp < max(azaz, azaz + azint))
            )
            print("ind", ind)
            print("len ind", len(ind))
            dum = sdata[ind[0], :]
            ind2 = np.argsort(dum[:, 6])
            if elflag == 0:
                elflag = 1
            else:
                ind2 = ind2[::-1]
                elflag = 0
            ddata = np.append(ddata, dum[ind2, :], axis=0)
            continue

        # x = ddata[:, 5].astype(np.float64)
        # y = ddata[:, 6].astype(np.float64)
        show_graph = True
        if show_graph is True:
            plt.figure()
            plt.plot(ddata[:, 5], ddata[:, 6])
            plt.grid()
            plt.xlabel("Az")
            plt.ylabel("El")
            plt.title(f"Optical Pointing Locus\nstar num = {str(len(ddata))}")
            plt.show()

        return ddata
