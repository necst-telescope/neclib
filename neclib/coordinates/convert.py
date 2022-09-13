__all__ = ["CoordCalculator"]

from typing import Tuple, TypeVar, Union

import astropy.constants as const
import astropy.units as u
from astropy.coordinates import (
    AltAz,
    BaseCoordinateFrame,
    EarthLocation,
    SkyCoord,
    get_body,
)
from astropy.time import Time

from neclib import logger
from ..parameters.pointing_error import PointingError
from ..typing import Number, PathLike


T = TypeVar("T", Number, u.Quantity)
# lon と lat の型が揃っていない場合には対応しなくていい


class CoordCalculator:
    """Calculate horizontal coordinate.

    Parameters
    ----------
    location
        Location of observatory.
    pointing_param_path
        Path to pointing parameter file.
    pressure
        Atmospheric pressure at the observation environment.
    temperature
        Temperature at the observation environment.
    relative_humidity
        Relative humidity at the observation environment.
    obswl
        Observing wavelength.

    Attributes
    ----------
    location: EarthLocation
        Location of observatory.
    pressure: Quantity
        Atmospheric pressure, to compute diffraction correction.
    temperature: Quantity
        Temperature, to compute diffraction correction.
    relative_humidity: Quantity or float
        Relative humidity, to compute diffraction correction.
    obswl: Quantity
        Observing wavelength, to compute diffraction correction.
    obsfreq: Quantity
        Observing frequency of EM-wave, to compute diffraction correction.

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

    def __init__(
        self,
        location: EarthLocation,
        pointing_param_path: PathLike,
        *,  # 以降の引数はキーワード引数（引数名=値）として受け取ることを強制する
        pressure: u.Quantity = None,
        temperature: u.Quantity = None,
        relative_humidity: Union[Number, u.Quantity] = None,
        obswl: u.Quantity = None,
        obsfreq: u.Quantity = None,
    ) -> None:
        if (obswl is not None) and (obsfreq is not None):
            if obswl != const.c / obsfreq:
                raise ValueError("Specify ``obswl`` or ``obs_freq``, not both.")

        self.location = location
        self.pointing_param_path = pointing_param_path
        self.pressure = pressure
        self.temperature = temperature
        self.relative_humidity = relative_humidity
        self.obswl = obswl
        if temperature is not None:
            self.temperature = temperature.to("deg_C", equivalencies=u.temperature())
        if obsfreq is not None:
            self.obswl = const.c / obsfreq

        self.pointing_error_corrector = PointingError.from_file(pointing_param_path)

        if pressure is None:
            logger.warning("pressure が未指定です。")
        if temperature is None:
            logger.warning("temperature が未指定です。")
        if relative_humidity is None:
            logger.warning("relative_humidity が未指定です。")
        if obswl is None:
            logger.warning("obswl が未指定です。")

    def _get_altaz_frame(self, obstime: Union[Number, Time]) -> AltAz:
        obstime = self._convert_obstime(obstime)
        return AltAz(
            obstime=obstime,
            location=self.location,
            pressure=self.pressure,
            temperature=self.temperature,
            relative_humidity=self.relative_humidity,
            obswl=self.obswl,
        )

    def _convert_obstime(self, obstime: Union[Number, Time]) -> Time:
        return obstime if isinstance(obstime, Time) else Time(obstime, format="unix")

    def get_altaz_by_name(
        self,
        name: str,
        obstime: Union[Number, Time],
    ) -> Tuple[u.Quantity, u.Quantity]:
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
        return self.pointing_error_corrector.refracted2encoder(altaz.az, altaz.alt)

    def get_altaz(
        self,
        lon: T,  # 変換前の経度
        lat: T,  # 変換前の緯度
        frame: Union[str, BaseCoordinateFrame],  # 変換前の座標系
        *,
        unit: Union[str, u.Unit] = None,
        obstime: Union[Number, Time],
    ) -> Tuple[u.Quantity, u.Quantity]:
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
        input_is_quantity = isinstance(lon, u.Quantity) and isinstance(lat, u.Quantity)
        if (not input_is_quantity) and (unit is None):
            raise ValueError("Specify unit for non-quantity input (lon, lat)")
        if not input_is_quantity:
            lon = u.Quantity(lon, unit=unit)
            lat = u.Quantity(lat, unit=unit)
        if frame == "altaz":
            frame = self._get_altaz_frame()
        altaz = SkyCoord(lon, lat, frame=frame).transform_to(
            self._get_altaz_frame(self._convert_obstime(obstime))
        )
        return self.pointing_error_corrector.refracted2encoder(altaz.az, altaz.alt)
