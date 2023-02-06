__all__ = ["CoordCalculator"]

import os
import time
from typing import List, Optional, Tuple, TypeVar, Union

import astropy.constants as const
import astropy.units as u
import numpy as np
from astropy.coordinates import (
    AltAz,
    BaseCoordinateFrame,
    EarthLocation,
    SkyCoord,
    get_body,
)
from astropy.time import Time

from .. import config, get_logger, utils
from ..core import disabled
from ..core.type_aliases import CoordFrameType, DimensionLess, UnitType
from .frame import parse_frame
from .pointing_error import PointingError

T = TypeVar("T", DimensionLess, u.Quantity)


class CoordCalculator:
    """Calculate horizontal coordinate.

    Parameters
    ----------
    location
        Location of observatory.
    pointing_param_path
        Path to pointing parameter file.
    pressure
        Atmospheric pressure at the observatory.
    temperature
        Temperature at the observatory.
    relative_humidity
        Relative humidity at the observatory.
    obswl
        Observing wavelength.
    obsfreq
        Observing frequency of EM-wave, to compute diffraction correction.

    Attributes
    ----------
    location: EarthLocation
        Location of observatory.
    pressure: Quantity
        Atmospheric pressure, to compute diffraction correction. If dimensionless value
        is given, it is assumed to be in ``hPa``.
    temperature: Quantity
        Temperature, to compute diffraction correction. If dimensionless value is given,
        it is assumed to be in ``K``.
    relative_humidity: Quantity or float
        Relative humidity, to compute diffraction correction.
    obswl: Quantity
        Observing wavelength, to compute diffraction correction. If dimensionless value
        is given, it is assumed to be in ``m``.

    Examples
    --------
    >>> location = EarthLocation("138.472153deg", "35.940874deg", "1386m")
    >>> path = "path/to/pointing_param.toml"
    >>> pressure = 850 << u.hPa
    >>> temperature = 300 << u.K
    >>> humid = 0.30
    >>> obswl = 230.5 << u.GHz
    >>> calculator = neclib.coordinates.CoordCalculator(
    ...     location, path, pressure=pressure, temperature=temperature,
    ...     relative_humidity=humid, obswl=obswl)

    """

    pressure = utils.get_quantity(default_unit="hPa")
    temperature = utils.get_quantity(default_unit="K")
    relative_humidity = utils.get_quantity(default_unit="")
    obswl = utils.get_quantity(default_unit="m")

    def __init__(
        self,
        location: EarthLocation,
        pointing_param_path: Optional[os.PathLike] = None,
        *,
        pressure: Optional[u.Quantity] = None,
        temperature: Optional[u.Quantity] = None,
        relative_humidity: Optional[Union[DimensionLess, u.Quantity]] = None,
        obswl: Optional[u.Quantity] = None,
        obsfreq: Optional[u.Quantity] = None,
    ) -> None:
        self.logger = get_logger(self.__class__.__name__)

        if (obswl is not None) and (obsfreq is not None):
            if obswl != const.c / obsfreq:  # type: ignore
                raise ValueError("Specify ``obswl`` or ``obs_freq``, not both.")

        self.location = location
        self.pointing_param_path = pointing_param_path
        self.pressure = pressure
        self.temperature = temperature
        self.relative_humidity = relative_humidity

        if obsfreq is not None:
            self.obswl = const.c / obsfreq  # type: ignore

        if pointing_param_path is not None:
            self.pointing_error_corrector = PointingError.from_file(pointing_param_path)
        else:
            self.logger.warning("Pointing error correction is disabled.")
            dummy = PointingError()
            dummy.refracted_to_apparent = lambda az, el: (az, el)
            self.pointing_error_corrector = dummy

        diffraction_params = ["pressure", "temperature", "relative_humidity", "obswl"]
        not_set = list(
            filter(lambda x: getattr(self, x) != getattr(self, x), diffraction_params)
        )
        if len(not_set) > 0:
            self.logger.warning(
                f"{not_set} are not given. Diffraction correction is disabled."
            )

    def _get_altaz_frame(self, obstime: Union[DimensionLess, Time]) -> AltAz:
        obstime = self._convert_obstime(obstime)
        return AltAz(obstime=obstime, **self.altaz_kwargs)

    def _convert_obstime(self, obstime: Union[DimensionLess, Time, None]) -> Time:
        if obstime is None:
            obstime = self._auto_schedule_obstime()
        return obstime if isinstance(obstime, Time) else Time(obstime, format="unix")

    def _auto_schedule_obstime(self, duration=1):
        """Automatically generate sequence of time."""
        now = time.time()
        frequency = config.antenna_command_frequency
        offset = config.antenna_command_offset_sec
        return Time(
            [now + offset + i / frequency for i in range(int(frequency * duration))],
            format="unix",
        )

    def get_body(self, name: str, obstime: T) -> SkyCoord:
        if not isinstance(obstime, Time):
            obstime = Time(obstime, format="unix")
        try:
            coord = get_body(name, obstime, self.location)
        except KeyError:
            coord = SkyCoord.from_name(name, frame="icrs")
        return np.broadcast_to(coord, obstime.shape)

    def get_altaz_by_name(
        self,
        name: str,
        obstime: Optional[Union[DimensionLess, Time]] = None,
    ) -> Tuple[u.Quantity, u.Quantity, List[float]]:
        """天体名から地平座標 az, el(alt) を取得する

        Parameters
        ----------
        name
            Name of celestial object.
        obstime
            Time the observation is done.

        Examples
        --------
        >>> calculator.get_altaz_by_name("M42", time.time())
        <SkyCoord (az, alt) in deg (274.55435678, -15.3762009)>

        """
        obstime = self._convert_obstime(obstime)
        coord = self.get_body(name, obstime)
        altaz = coord.transform_to(self._get_altaz_frame(obstime))
        return (
            *self.pointing_error_corrector.refracted_to_apparent(altaz.az, altaz.alt),
            obstime.unix,
        )

    def get_altaz(
        self,
        lon: T,  # 変換前の経度
        lat: T,  # 変換前の緯度
        frame: Union[str, BaseCoordinateFrame],  # 変換前の座標系
        *,
        unit: Optional[UnitType] = None,
        obstime: Optional[Union[DimensionLess, Time]] = None,
    ) -> Tuple[u.Quantity, u.Quantity, List[float]]:
        """Get horizontal coordinate from longitude and latitude in arbitrary frame.

        Parameters
        ----------
        lon
            Longitude of target.
        lat
            Latitude of target.
        frame
            Coordinate frame, in which ``lon`` and ``lat`` are given.
        unit
            Angular unit in which ``lon`` and ``lat`` are given. If they are given as
            ``Quantity``, this parameter will be ignored.
        obstime
            Time the observation is done.

        Examples
        --------
        >>> calculator.get_altaz(30 << u.deg, 45 << u.deg, "fk5", obstime=time.time())
        <SkyCoord (az, alt) in deg (344.21675916, -6.43235393)>

        """
        obstime = self._convert_obstime(obstime)
        lon, lat = utils.get_quantity(lon, lat, unit=unit)  # type: ignore
        if getattr(frame, "name", frame) == "altaz":
            frame = self._get_altaz_frame(time.time())
            (
                apparent_az,
                apparent_alt,
            ) = self.pointing_error_corrector.refracted_to_apparent(lon, lat)
            return (
                np.broadcast_to(apparent_az, obstime.shape) << apparent_az.unit,
                np.broadcast_to(apparent_alt, obstime.shape) << apparent_alt.unit,
                obstime.unix,
            )
        elif isinstance(frame, str):
            frame = parse_frame(frame)

        altaz = SkyCoord(lon, lat, frame=frame).transform_to(
            self._get_altaz_frame(obstime)
        )
        return (
            *self.pointing_error_corrector.refracted_to_apparent(altaz.az, altaz.alt),
            obstime.unix,
        )

    @staticmethod
    def get_position_angle(a: Tuple[T, T], b: Tuple[T, T], /) -> u.Quantity:
        if a[0] == b[0]:
            position_angle = (np.pi / 2 * u.rad) * np.sign(b[1] - a[1])
        else:
            position_angle = np.arctan((b[1] - a[1]) / (b[0] - a[0])) << u.rad
            position_angle += (np.pi if b[0] < a[0] else 0) * u.rad
        return position_angle

    @classmethod
    def get_extended(
        cls,
        a: Tuple[T, T],
        b: Tuple[T, T],
        /,
        *,
        length: T,
    ) -> Tuple[T, T]:
        pa = cls.get_position_angle(a, b)
        d_lon, d_lat = length * np.cos(pa), length * np.sin(pa)
        return a[0] - d_lon, a[1] - d_lat

    @property
    def altaz_kwargs(self) -> dict:
        return dict(
            location=self.location,
            pressure=self.pressure,
            temperature=self.temperature.to(u.deg_C, equivalencies=u.temperature()),
            relative_humidity=self.relative_humidity,
            obswl=self.obswl,
        )

    def get_skycoord(
        self,
        lon: T,
        lat: T,
        distance: Optional[T] = None,
        *,
        frame: CoordFrameType,
        obstime: Union[float, List[float]],
        unit: Optional[UnitType] = None,
    ) -> SkyCoord:
        obstime = Time(obstime, format="unix")
        lon_unit = lon.unit if hasattr(lon, "unit") else 1
        lat_unit = lat.unit if hasattr(lat, "unit") else 1
        lon = np.broadcast_to(lon, obstime.shape) * lon_unit
        lat = np.broadcast_to(lat, obstime.shape) * lat_unit
        unit = dict(unit=unit) if unit is not None else {}
        args = [lon, lat]
        if distance is not None:
            args.append(distance)
        if isinstance(frame, str):
            frame = parse_frame(frame)

        return SkyCoord(
            *args, frame=frame, obstime=obstime, **self.altaz_kwargs, **unit
        )

    def transform_to(self, coord: SkyCoord, to: CoordFrameType) -> SkyCoord:
        if isinstance(to, str):
            to = parse_frame(to)
        return coord.transform_to(to)

    @disabled
    def sidereal_offset(
        self,
        reference: Tuple[T, T, CoordFrameType],
        offset: Tuple[T, T, CoordFrameType],
        t: List[float],
        unit: UnitType,
    ) -> Tuple[T, T]:
        obstime = Time(t, format="unix")
        ref = self.get_skycoord(
            *reference[:2], frame=reference[2], obstime=obstime, unit=unit
        )
        ref_in_offset_frame = self.transform_to(ref, offset[2])
        return (
            ref_in_offset_frame.data.lon.to_value(unit) + offset[0],
            ref_in_offset_frame.data.lat.to_value(unit) + offset[1],
        )
