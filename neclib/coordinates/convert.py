__all__ = ["CoordCalculator"]

import os
import time
from typing import Sequence, Tuple, TypeVar, Union

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
from ..parameters.pointing_error import PointingError
from ..typing import Number


T = TypeVar("T", Number, u.Quantity)


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

    pressure: u.Quantity = utils.get_quantity(default_unit="hPa")
    temperature: u.Quantity = utils.get_quantity(default_unit="K")
    relative_humidity: u.Quantity = utils.get_quantity(default_unit="")
    obswl: u.Quantity = utils.get_quantity(default_unit="m")

    def __init__(
        self,
        location: EarthLocation,
        pointing_param_path: os.PathLike = None,
        *,
        pressure: u.Quantity = None,
        temperature: u.Quantity = None,
        relative_humidity: Union[Number, u.Quantity] = None,
        obswl: u.Quantity = None,
        obsfreq: u.Quantity = None,
    ) -> None:
        self.logger = get_logger(self.__class__.__name__)

        if (obswl is not None) and (obsfreq is not None):
            if obswl != const.c / obsfreq:
                raise ValueError("Specify ``obswl`` or ``obs_freq``, not both.")

        self.location = location
        self.pointing_param_path = pointing_param_path
        self.pressure = pressure
        self.temperature = temperature
        self.relative_humidity = relative_humidity

        if obsfreq is not None:
            self.obswl = const.c / obsfreq

        if pointing_param_path is not None:
            self.pointing_error_corrector = PointingError.from_file(pointing_param_path)
        else:
            self.logger.warning("Pointing error correction is disabled.")
            dummy = PointingError()
            dummy.refracted2apparent = lambda az, el: (az, el)
            self.pointing_error_corrector = dummy

        diffraction_params = ["pressure", "temperature", "relative_humidity", "obswl"]
        not_set = list(filter(lambda x: getattr(self, x) is None, diffraction_params))
        if len(not_set) > 0:
            self.logger.warning(
                f"{not_set} are not given. Diffraction correction is disabled."
            )

    def _get_altaz_frame(self, obstime: Union[Number, Time]) -> AltAz:
        obstime = self._convert_obstime(obstime)
        if self.temperature is not None:
            self.temperature = self.temperature.to(
                "deg_C", equivalencies=u.temperature()
            )
        return AltAz(
            obstime=obstime,
            location=self.location,
            pressure=self.pressure,
            temperature=self.temperature,
            relative_humidity=self.relative_humidity,
            obswl=self.obswl,
        )

    def _convert_obstime(self, obstime: Union[Number, Time, None]) -> Time:
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

    def get_altaz_by_name(
        self,
        name: str,
        obstime: Union[Number, Time] = None,
    ) -> Tuple[u.Quantity, u.Quantity, Sequence[float]]:
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
        try:
            coord = get_body(name, obstime)
        except KeyError:
            coord = SkyCoord.from_name(name)
        altaz = coord.transform_to(self._get_altaz_frame(obstime))
        return [
            *self.pointing_error_corrector.refracted2apparent(altaz.az, altaz.alt),
            obstime.unix,
        ]

    def get_altaz(
        self,
        lon: T,  # 変換前の経度
        lat: T,  # 変換前の緯度
        frame: Union[str, BaseCoordinateFrame],  # 変換前の座標系
        *,
        unit: Union[str, u.Unit] = None,
        obstime: Union[Number, Time] = None,
    ) -> Tuple[u.Quantity, u.Quantity, Sequence[float]]:
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
        lon, lat = utils.get_quantity(lon, lat, unit=unit)
        if getattr(frame, "name", frame) == "altaz":
            frame = self._get_altaz_frame(time.time())
            (
                apparent_az,
                apparent_alt,
            ) = self.pointing_error_corrector.refracted2apparent(lon, lat)
            return [
                np.broadcast_to(apparent_az, obstime.shape) << apparent_az.unit,
                np.broadcast_to(apparent_alt, obstime.shape) << apparent_alt.unit,
                obstime.unix,
            ]

        altaz = SkyCoord(lon, lat, frame=frame).transform_to(
            self._get_altaz_frame(obstime)
        )
        return [
            *self.pointing_error_corrector.refracted2apparent(altaz.az, altaz.alt),
            obstime.unix,
        ]
