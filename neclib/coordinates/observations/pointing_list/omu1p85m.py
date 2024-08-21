from typing import Tuple

import pandas as pd

from astropy.coordinates import Angle
from astropy import units as u

from ....core import config
from .pointing_list import PointingList


class OMU1p85m(PointingList):
    def _catalog_to_pandas(self, filename: str):
        catalog_raw = self.readlines_file(filename)
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

    def filter(self, magnitude: Tuple[float, float]) -> pd.DataFrame:
        catalog = self.catalog
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
