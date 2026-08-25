import math
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from astropy import units as u
from astropy.time import Time
from matplotlib import pyplot as plt

from ...core import config, get_logger
from ..convert import CoordCalculator

logger = get_logger(__name__)


class BSC5ParseError(ValueError):
    """Raised when a BSC5 fixed-width record is malformed."""


def _field(line: str, first_byte: int, last_byte: int) -> str:
    """Return an inclusive, 1-origin byte range from a BSC5 record."""
    record = line.rstrip("\r\n")
    if first_byte < 1 or last_byte < first_byte:
        raise ValueError("invalid BSC5 byte range")
    if len(record) < last_byte:
        raise BSC5ParseError(
            f"record is too short: need byte {last_byte}, got {len(record)}"
        )
    return record[first_byte - 1 : last_byte]


def _sort_serpentine_bins(
    data: pd.DataFrame, lower: float, upper: float, width: float
) -> pd.DataFrame:
    """Sort non-empty half-open azimuth bins in alternating elevation order."""
    chunks = []
    ascending = True
    for bin_lower in np.arange(lower, upper, width):
        bin_upper = min(bin_lower + width, upper)
        in_bin = data[(data["az"] >= bin_lower) & (data["az"] < bin_upper)]
        if in_bin.empty:
            continue
        chunks.append(in_bin.sort_values("el", ascending=ascending))
        ascending = not ascending
    return pd.concat(chunks, ignore_index=True) if chunks else data.iloc[0:0].copy()


class OpticalPointingSpec:
    def __init__(self, time: Union[float, str], format: str) -> None:
        self.calc = CoordCalculator(
            config.location,
            pointing_err_file=config.antenna_pointing_parameter_path,
        )
        # This planning conversion intentionally does not apply atmospheric
        # refraction. Supplying a zero pressure expresses that explicitly and
        # avoids mutating the shared coordinate logger just to hide its warning.
        self.calc.pressure = 0 * u.hPa
        self.calc.temperature = 273.15 * u.K
        self.calc.relative_humidity = 0.0
        self.now = Time(time, format=format)
        self.obsdatetime = self.now.to_datetime()

    def readlines_file(self, filename: str) -> List[str]:
        with open(filename, mode="r") as file:
            contents = file.readlines()
        return contents

    def _parse_catalog_line_fixed_width(
        self, line: str
    ) -> Optional[Dict[str, Union[int, str, float, u.Quantity]]]:
        hr = int(_field(line, 1, 4))
        if not _field(line, 76, 90).strip():
            # BSC5 retains 14 removed objects without primary coordinates.
            return None

        name = _field(line, 5, 14).strip()

        # Convert sexagesimal to degrees numerically rather than via
        # Angle("12h34m56.7s") / Quantity arithmetic. Both are correct, but the
        # string-parsing and unit-conversion machinery costs ~100 us per star,
        # which dominates the read of a ~9000-line catalog. Same result, minus
        # the per-star overhead.
        ra = (
            (
                float(_field(line, 76, 77))  # hour
                + float(_field(line, 78, 79)) / 60.0  # minute
                + float(_field(line, 80, 83)) / 3600.0  # second
            )
            * 15.0  # hour angle -> degree
        ) * u.deg

        dec_deg = (
            float(_field(line, 85, 86))  # degree
            + float(_field(line, 87, 88)) / 60.0  # arcmin
            + float(_field(line, 89, 90)) / 3600.0  # arcsec
        )
        dec_sign = _field(line, 84, 84)
        if dec_sign not in {"+", "-"}:
            raise BSC5ParseError(f"HR {hr}: invalid Dec sign {dec_sign!r}")
        if dec_sign == "-":
            dec_deg = -dec_deg
        dec = dec_deg * u.deg

        multiple = _field(line, 44, 44)
        vmag = float(_field(line, 103, 107))
        pmra = float(_field(line, 149, 154))  # arcsec/yr, mu_alpha*cos(delta)
        pmdec = float(_field(line, 155, 160))  # arcsec/yr

        return {
            "hr": hr,
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
    ) -> Optional[Dict[str, Union[int, str, float, u.Quantity]]]:
        if not line.strip():
            return None

        return self._parse_catalog_line_fixed_width(line)

    def _catalog_to_pandas(self, catalog_raw: List[str]):
        hr_data = []
        name_data = []
        ra_data = []
        dec_data = []
        multiple_data = []
        vmag_data = []
        pmra_data = []
        pmdec_data = []

        # J2000.0 から観測時刻までの経過年数(ユリウス年)を算出
        dt_years = self.now.jyear - 2000.0

        for line_no, line in enumerate(catalog_raw, start=1):
            try:
                parsed = self._parse_catalog_line(line)
                if parsed is None:
                    continue

                ra = parsed["ra"]
                dec = parsed["dec"]
                pmra = parsed["pmra"]
                pmdec = parsed["pmdec"]

                # ==========================================================
                # 固有運動(Proper Motion)の厳密な補正処理
                # ==========================================================
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
            except (BSC5ParseError, ValueError) as exc:
                hr_text = line[0:4] if len(line) >= 4 else "????"
                raise BSC5ParseError(
                    f"BSC5 parse failed at line={line_no}, HR={hr_text!r}: {exc}"
                ) from exc

            hr_data.append(parsed["hr"])
            ra_data.append(ra.to_value(u.deg))
            dec_data.append(dec.to_value(u.deg))
            multiple_data.append(parsed["multiple"])
            vmag_data.append(parsed["vmag"])
            pmra_data.append(pmra)
            pmdec_data.append(pmdec)
            name_data.append(parsed["name"])

        # One vectorized coordinate conversion for the whole catalog. Converting
        # star-by-star costs ~3.4 ms each (astropy builds a fresh frame and
        # re-runs the erfa astrometry setup per call), which is ~30 s for a
        # 9000-star catalog; batching it is ~3000x faster for an identical
        # result, since the per-call overhead is paid once instead of N times.
        #
        altaz = self.to_altaz(
            target=(np.array(ra_data) * u.deg, np.array(dec_data) * u.deg),
            frame="fk5",
        )
        az_data = np.atleast_1d(altaz.az.to_value(u.deg))
        el_data = np.atleast_1d(altaz.alt.to_value(u.deg))

        data = pd.DataFrame(
            {
                "hr": hr_data,
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

    def sort(
        self,
        catalog_file: str,
        magnitude: Tuple[float, float],
        *,
        show_graph: bool = True,
    ):
        az_range = config.antenna_drive_warning_limit_az

        catalog_raw = self.readlines_file(filename=catalog_file)
        catalog = self._catalog_to_pandas(catalog_raw=catalog_raw)
        catalog = self._filter(catalog, magnitude)

        sdata = catalog.sort_values("az", ignore_index=True)  # sort by az

        azint = 25 * u.deg
        ddata = _sort_serpentine_bins(
            sdata,
            az_range.lower.value,
            az_range.upper.value,
            azint.value,
        )

        x = ddata["az"].values.astype(np.float64)
        y = ddata["el"].values.astype(np.float64)

        if show_graph:
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

    def resolve_mount_targets(self, sorted_data: pd.DataFrame) -> pd.DataFrame:
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

        The fix is *not* to instead anchor the first star to wherever the
        antenna happens to be idling right now - that's the same "pick
        whichever branch is closest" shortcut in disguise, it just moves the
        problem to star 0. The first star gets its own true azimuth, as-is.
        Every following star then picks whichever 360deg-equivalent angle is
        closest to the *previous star's* resolved one, constrained to stay
        within the critical drive range. This keeps every step - including
        the very first - equal to the stars' true angular separation, with
        no dependence on the antenna's starting position.

        Callers should *not* drive the whole plan off ``mount_az``: sending
        raw AltAz with ``az_target_mode="mount"`` bypasses
        ``PathFinder.track()``, which is what re-derives Az/El every command
        cycle and therefore what makes the antenna follow the star against
        Earth's rotation. Driving a static AltAz value would silently drop
        sidereal tracking, and since these numbers are a snapshot taken at
        plan time, late targets in a ~20 min run would be off by ~1deg.

        Instead use ``mount_az[0]`` for a single explicit mount-frame slew
        before the run, to place the antenna on the branch this plan intends,
        and then drive every star (including the first) with ordinary RA/Dec
        tracking commands. Once the antenna sits on the intended branch, the
        nearest 360deg-equivalent for each subsequent star *is* the intended
        one, so the drive-limit optimizer stays on that branch by itself and
        tracking is fully preserved. See ``OpticalPointing._pin_unwrap_branch``
        in necst.

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
        prev = None
        for raw_az in sorted_data["az"]:
            raw_az = float(raw_az)
            if prev is None:
                resolved = raw_az
            else:
                k_min = math.ceil((lower - raw_az) / 360.0)
                k_max = math.floor((upper - raw_az) / 360.0)
                if k_min > k_max:
                    # No 360deg-equivalent branch fits in the critical range at
                    # all (shouldn't happen for a sane drive range, but don't
                    # silently pick something out of range if it does).
                    logger.warning(
                        f"raw az={raw_az:.3f}deg has no equivalent angle "
                        f"within critical drive range {critical}."
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
        az_column = "mount_az" if "mount_az" in sorted_data else "az"
        time_list = []
        for i in range(len(sorted_data) - 1):
            # abs(): only the size of the move matters, not its direction.
            # The unsigned delta was previously compared directly, which
            # silently mis-picked the axis whenever the El zigzag moved
            # downward (a negative delta_el could beat a positive delta_az
            # despite covering less distance), and left `t` unassigned
            # (UnboundLocalError) on the rare exact tie.
            delta_az = abs(sorted_data[az_column][i + 1] - sorted_data[az_column][i])
            delta_el = abs(sorted_data["el"][i + 1] - sorted_data["el"][i])
            # Az and El drive simultaneously, so the move takes as long as
            # whichever axis is slower to arrive, not just one axis's time.
            t = max(delta_az / az_speed, delta_el / el_speed) + 30.0
            time_list.append(t)

        t_tot = sum(time_list)
        return t_tot
