import logging
import math
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from astropy import units as u
from astropy.coordinates import Angle
from astropy.time import Time
from matplotlib import pyplot as plt

from ...core import config, get_logger
from ..convert import CoordCalculator
from ..convert import logger as _convert_logger

logger = get_logger(__name__)


class OpticalPointingSpec:
    def __init__(self, time: Union[float, str], format: str) -> None:
        self.calc = CoordCalculator(
            config.location,
            pointing_err_file=config.antenna_pointing_parameter_path,
        )
        self.now = Time(time, format=format)
        self.obsdatetime = self.now.to_datetime()

    def readlines_file(self, filename: str) -> List[str]:
        with open(filename, mode="r") as file:
            contents = file.readlines()
        return contents

    def _parse_catalog_line_fixed_width(
        self, line: str
    ) -> Dict[str, Union[str, float, u.Quantity]]:
        if len(line) < 160:
            raise ValueError("line too short for fixed-width BSC5 parser")

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

        multiple = line[43:44]
        vmag = float(line[103:107])
        pmra = float(line[149:154])  # BSC5: arcsec/yr, mu_alpha*cos(delta)
        pmdec = float(line[154:160])  # BSC5: arcsec/yr

        return {
            "name": name,
            "ra": ra,
            "dec": dec,
            "multiple": multiple,
            "vmag": vmag,
            "pmra": pmra,
            "pmdec": pmdec,
        }

    def _parse_catalog_line(
        self, line: str
    ) -> Optional[Dict[str, Union[str, float, u.Quantity]]]:
        if not line.strip():
            return None

        return self._parse_catalog_line_fixed_width(line)

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

        total = len(catalog_raw)
        logger.info(f"Computing Az/El for {total} catalog stars (visibility check)...")
        # Weather isn't wired into this throwaway CoordCalculator (see to_altaz),
        # so it would otherwise warn once per star; that's expected here, not a
        # real problem, so mute it for the duration of this loop.
        convert_level = _convert_logger.level
        _convert_logger.setLevel(logging.ERROR)
        progress_step = max(1, total // 20)
        try:
            for i, line in enumerate(catalog_raw):
                if i % progress_step == 0:
                    logger.info(f"Visibility check: {i}/{total} stars...")
                try:
                    parsed = self._parse_catalog_line(line)
                    if parsed is None:
                        continue

                    name = parsed["name"]
                    ra = parsed["ra"]
                    dec = parsed["dec"]
                    multiple = parsed["multiple"]
                    vmag = parsed["vmag"]
                    pmra = parsed["pmra"]
                    pmdec = parsed["pmdec"]

                    # ==========================================================
                    # 固有運動(Proper Motion)の厳密な補正処理
                    # ==========================================================
                    # J2000.0 から観測時刻までの経過年数(ユリウス年)を算出
                    dt_years = self.now.jyear - 2000.0

                    # 赤緯(Dec)のコサインを計算 (np.cosはラジアンを要求するため変換)
                    cos_dec = np.cos(dec.to(u.rad).value)

                    # RAの補正:
                    # 1. カタログのpmraは天球上の見かけの移動距離(μ_α * cosδ)なので、
                    #    実際のRA座標の移動量に戻すために cos_dec で割る。
                    #    (※極付近でcos_decが0に近くなるゼロ除算を防ぐため安全対策を入れる)
                    # 2. 秒角(arcsec)から度(deg)に変換するため 3600 で割る。
                    if abs(cos_dec) > 1e-6:
                        delta_ra_deg = (pmra / cos_dec) * dt_years / 3600.0
                        ra = ra + (delta_ra_deg * u.deg)

                    # Decの補正:
                    # 秒角(arcsec)から度(deg)に変換するため 3600 で割る。
                    delta_dec_deg = pmdec * dt_years / 3600.0
                    dec = dec + (delta_dec_deg * u.deg)
                    # ==========================================================

                    # 補正済みの (ra, dec) を使って AltAz(方位角/仰角) に変換
                    altaz = self.to_altaz(target=(ra, dec), frame="fk5")

                except Exception:
                    continue

                ra_data.append(ra.value)
                dec_data.append(dec.value)
                multiple_data.append(multiple)
                vmag_data.append(vmag)
                pmra_data.append(pmra)
                pmdec_data.append(pmdec)
                name_data.append(name)
                az_data.append(altaz.az.value)
                el_data.append(altaz.alt.value)
            logger.info(f"Visibility check: {total}/{total} stars done.")
        finally:
            _convert_logger.setLevel(convert_level)

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
            & (catalog["pmra"].abs() <= 1.0)
            & (catalog["pmdec"].abs() <= 1.0)
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
        azint = 25 * u.deg

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
            ddata = pd.concat([ddata, ind2])
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

    def resolve_mount_targets(
        self, sorted_data: pd.DataFrame, current_az: float
    ) -> pd.DataFrame:
        """Resolve each star's azimuth into the antenna's continuous mount domain.

        ``sorted_data["az"]`` is astropy's raw apparent azimuth, always folded
        into [0, 360)deg; it has no notion of the antenna's actual (unwrapped)
        mechanical position. Driving straight from that raw value forces the
        antenna-side drive-limit optimizer to pick *some* 360deg-equivalent
        angle close to wherever the antenna currently is, independently for
        every single star. Since that choice ignores where the *next* star
        will be, two stars that are only a few degrees apart in the sky can
        still end up several hundred degrees apart in chosen mount angle,
        forcing a wasted full-range slew between them (see
        necst-telescope/necst#481).

        Instead, walk the already-sorted stars in order and pick, for each one,
        whichever 360deg-equivalent angle is closest to the previously resolved
        one (starting from the antenna's actual current azimuth), constrained to
        stay within the critical drive range. This keeps consecutive moves to
        their true angular separation and must be sent with
        ``az_target_mode="mount"`` so the drive layer doesn't re-fold it.

        Note that a plan spanning most of the sky in azimuth (as a full
        catalog sweep does) cannot stay chained to one 360deg branch forever -
        at some point the drive range itself forces a jump back to a lower
        branch. Naively minimizing each step against the previous one without
        this constraint lets small per-step "improvements" compound into an
        unbounded drift (see necst-telescope/necst#481, where this went as far
        as ~720deg before the bug was caught). Clamping the candidate branch to
        the critical range up front keeps each individual result valid and
        limits the drift to the unavoidable "unwind" jumps.
        """
        critical = config.antenna_drive_critical_limit_az
        lower, upper = critical.lower.value, critical.upper.value

        mount_az = []
        prev = float(current_az)
        for raw_az in sorted_data["az"]:
            k_min = math.ceil((lower - raw_az) / 360.0)
            k_max = math.floor((upper - raw_az) / 360.0)
            if k_min > k_max:
                # No 360deg-equivalent branch fits in the critical range at all
                # (shouldn't happen for a sane drive range, but don't silently
                # pick something out of range if it does).
                logger.warning(
                    f"raw az={raw_az:.3f}deg has no equivalent angle within "
                    f"critical drive range {critical}."
                )
                k = round((prev - raw_az) / 360.0)
            else:
                k = round((prev - raw_az) / 360.0)
                k = max(k_min, min(k_max, k))
            resolved = raw_az + 360.0 * k
            mount_az.append(resolved)
            prev = resolved

        result = sorted_data.copy()
        result["mount_az"] = mount_az
        return result

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
