"""Coordinate conversion functions.

This module contains functions for coordinate conversion and types for coordinate
handling. The intention of the custom type definitions is to avoid unintended coordinate
conversions which can be caused by the use of highly automated ``SkyCoord`` objects.

"""

__all__ = ["CoordinateDelta", "CoordCalculator", "CoordinateLike"]

import os
from dataclasses import dataclass, fields
from typing import Any, ClassVar, Dict, Optional, Tuple, Type, TypeVar, Union, overload

import astropy.units as u
import numpy as np
from astropy.coordinates import BaseCoordinateFrame, EarthLocation, SkyCoord, get_body
from astropy.coordinates.erfa_astrom import ErfaAstromInterpolator, erfa_astrom
from astropy.time import Time

from ..core import config, get_logger
from ..core.normalization import QuantityValidator, get_quantity
from ..core.types import Array, CoordFrameType, DimensionLess, UnitType
from .frame import parse_frame
from .pointing_error import PointingError

CoordinateLike = TypeVar("CoordinateLike", SkyCoord, BaseCoordinateFrame)
logger = get_logger(__name__, throttle_duration_sec=10)


class to_astropy_type:
    @overload
    @staticmethod
    def time(
        time: Union[str, int, float, Array[str], Time, Array[Union[int, float]]], /
    ) -> Time:
        ...

    @overload
    @staticmethod
    def time(time: None, /) -> None:
        ...

    @overload
    @staticmethod
    def time(
        *times: Union[str, int, float, Array[str], Time, Array[Union[int, float]]]
    ) -> Tuple[Time, ...]:
        ...

    @staticmethod
    def time(
        *times: Optional[
            Union[str, int, float, Time, Array[Union[int, float]], Array[str]]
        ]
    ) -> Optional[Union[Time, Tuple[Time, ...]]]:
        if (len(times) == 0) or (times[0] is None):
            return

        ret = []
        for time in times:
            if isinstance(time, Time):
                ret.append(time)
            elif isinstance(time, str):
                ret.append(Time(time))
            else:
                ret.append(Time(time, format="unix"))
        return tuple(ret) if len(ret) > 1 else ret[0]

    @overload
    @staticmethod
    def frame(
        frame: Union[str, BaseCoordinateFrame, Type[BaseCoordinateFrame]], /
    ) -> BaseCoordinateFrame:
        ...

    @overload
    @staticmethod
    def frame(frame: None, /) -> None:
        ...

    @overload
    @staticmethod
    def frame(
        *frames: Union[str, BaseCoordinateFrame, Type[BaseCoordinateFrame]]
    ) -> Tuple[BaseCoordinateFrame, ...]:
        ...

    @staticmethod
    def frame(
        *frames: Optional[Union[str, BaseCoordinateFrame, Type[BaseCoordinateFrame]]]
    ) -> Optional[Union[BaseCoordinateFrame, Tuple[BaseCoordinateFrame, ...]]]:
        if (len(frames) == 0) or (frames[0] is None):
            return

        ret = []
        for frame in frames:
            if isinstance(frame, BaseCoordinateFrame):
                ret.append(frame)
            elif isinstance(frame, str):
                ret.append(parse_frame(frame))
            elif callable(frame) and issubclass(frame, BaseCoordinateFrame):
                ret.append(frame())
            else:
                raise TypeError(f"Got invalid frame of type {type(frame)}: {frame}")
        return tuple(ret) if len(ret) > 1 else ret[0]


@dataclass
class Coordinate:
    lon: Union[DimensionLess, u.Quantity]
    lat: Union[DimensionLess, u.Quantity]
    frame: Union[Type[BaseCoordinateFrame], BaseCoordinateFrame, str]
    distance: Optional[Union[DimensionLess, u.Quantity]] = None
    time: Optional[Union[DimensionLess, Time]] = None
    unit: Optional[UnitType] = None

    _calc: ClassVar["CoordCalculator"]

    def __post_init__(self) -> None:
        if (self.lon is None) or (self.lat is None) or (self.frame is None):
            raise TypeError("Either `name` or `lon`, `lat` and `frame` must be given.")

        self.lon = get_quantity(self.lon, unit=self.unit)
        self.lat = get_quantity(self.lat, unit=self.unit)
        if self.distance is not None:
            # FIXME: invalid unit
            self.distance = get_quantity(self.distance, unit=self.unit)
        self.time = to_astropy_type.time(self.time)
        self.frame = to_astropy_type.frame(self.frame)

    @property
    def skycoord(self) -> SkyCoord:
        """SkyCoord object that represents this coordinate."""
        frame = self._normalize_frame(self.frame)
        kwargs = dict(obstime=self.time, **self._calc.altaz_kwargs)

        # To avoid the following error, attributes of current frame (self.frame)
        # shouldn't be passed as kwargs. Currently the filtering is applied implicitly
        # but this can lead to unexpected behavior, so this may emit warning in the
        # future.
        # ```Cannot specify frame attribute 'obstime' directly as an argument to
        # SkyCoord because a frame instance was passed in. Either pass a frame class,
        # or modify the frame attributes of the input frame instance.````
        _ = [kwargs.pop(k, None) for k in frame.frame_attributes]

        broadcasted = self.broadcasted
        args = [broadcasted.lon, broadcasted.lat]
        if self.distance is not None:
            args.append(broadcasted.distance)  # type: ignore
        return SkyCoord(*args, frame=frame, **kwargs)

    def _normalize_frame(
        self, frame: Union[Type[BaseCoordinateFrame], BaseCoordinateFrame]
    ) -> BaseCoordinateFrame:
        frame_kwargs = {}

        # Time dependent coordinates. Maybe more, but FK4 shouldn't be included here.
        if frame.name in ("altaz", "gcrs"):  # type: ignore
            frame_kwargs.update(obstime=self.time)

        if frame.name in ("altaz",):  # type: ignore
            frame_kwargs.update(self._calc.altaz_kwargs)

        if isinstance(frame, BaseCoordinateFrame):
            frame = frame.replicate_without_data(**frame_kwargs)
        elif callable(frame):
            frame = frame(**frame_kwargs)
        else:
            raise TypeError(f"Got invalid frame of type {type(frame)}: {frame}")

        return frame

    def transform_to(self, frame: CoordFrameType, /) -> "Coordinate":
        """Transform celestial coordinate between any frames.

        No time conversion is performed, so this operation on `Coordinate` object with
        no `time` attached can fail, depending on the target frame.

        Parameters
        ----------
        frame
            The frame to convert to.

        Returns
        -------
        The converted coordinates.

        """
        frame = to_astropy_type.frame(frame)
        frame = self._normalize_frame(frame)

        if (self.time is None) and (
            (getattr(self.frame, "obstime", ...) is None)
            or (getattr(frame, "obstime", ...) is None)
        ):
            raise ValueError(
                "Cannot transform coordinate without time attached to it. "
                "Please attach a time to the coordinate, or use `transform_to_time` "
                "to transform to a frame with a specific time."
            )

        # Interpolate astrometric parameters, for better performance.
        # https://docs.astropy.org/en/stable/coordinates/index.html#improving-performance-for-arrays-of-obstime
        with erfa_astrom.set(ErfaAstromInterpolator(300 * u.s)):
            return self.__class__.from_skycoord(self.skycoord.transform_to(frame))

    def cartesian_offset_by(self, offset: "CoordinateDelta", /) -> "Coordinate":
        """Calculate coordinates at the given offset from this coordinate.

        Parameters
        ----------
        offset
            Offset from this coordinate.

        Returns
        -------
        Coordinates at the given offset.

        Examples
        --------
        >>> coord = calc.coord.from_name("Sun", time.time())
        >>> coord.cartesian_offset_by(
        ...     neclib.coordinates.CoordinateDelta(1 * u.deg, 1 * u.deg))
        Coordinate(
            lon=<Longitude 6.20805658 rad>,
            lat=<Latitude -0.03254802 rad>,
            frame=<GCRS Frame (
                obstime=1678968349.001554,
                obsgeoloc=(-3548179.23395423, 3753814.11380175, 3731512.91152004) m,
                obsgeovel=(-273.72298624, -259.34513153, 0.62044525) m / s)>,
            time=<Time object: scale='utc' format='unix' value=1678968349.001554>)

        """
        if not isinstance(offset, CoordinateDelta):
            raise TypeError(
                f"Expected `CoordinateDelta` object, but got {type(offset).__name__}"
            )
        coord_in_offset_frame = self.transform_to(offset.frame)
        lon: u.Quantity = coord_in_offset_frame.lon + offset.d_lon  # type: ignore
        lat: u.Quantity = coord_in_offset_frame.lat + offset.d_lat  # type: ignore
        return self.__class__(
            lon=lon, lat=lat, distance=self.distance, frame=offset.frame, time=self.time
        )

    @classmethod
    def from_skycoord(cls, coord: SkyCoord, /):
        return cls(
            lon=coord.spherical.lon,  # type: ignore
            lat=coord.spherical.lat,  # type: ignore
            distance=getattr(coord.data, "distance", None),
            frame=coord.frame.replicate_without_data(),
            time=getattr(coord, "obstime", None),
        )

    def replicate(self, **kwargs: Any):
        _fields = {
            f.name: kwargs.get(f.name, getattr(self, f.name)) for f in fields(self)
        }
        return self.__class__(**_fields)

    def to_apparent_altaz(self) -> "ApparentAltAzCoordinate":
        """Convert celestial coordinate in any frame to telescope frame.

        This method converts the given ``coord`` to AltAz frame, taking into account
        the pointing error correction and the sidereal motion.

        Returns
        -------
        The converted coordinates, in AltAz frame.

        Notes
        -----
        If the coordinate object is already in the AltAz frame, this method simply
        returns the broadcasted version of it. This is because coordinates in AltAz
        frame should have already accounted for the sidereal motion. Therefore, no
        additional tracking calculations are necessary, only pointing error correction.

        """
        if self.time is None:
            raise ValueError("time is not given.")

        if self.frame.name == "altaz":  # type: ignore
            altaz = self.broadcasted
        else:
            altaz = self.transform_to("altaz")

        az, alt = self._calc.pointing_err.refracted_to_apparent(altaz.lon, altaz.lat)
        return ApparentAltAzCoordinate(az=az, alt=alt, time=self.time)

    @property
    def broadcasted(self) -> "Coordinate":
        if self.time is None:
            return self

        if self.lon.shape != self.lat.shape:
            raise ValueError(
                "`lon` and `lat` must have the same shape, but are "
                f"{self.lon.shape} and {self.lat.shape}."
            )
        elif self.lon.shape == self.time.shape:
            return self

        if self.lon.isscalar or (self.lon.size == 1):
            lon: u.Quantity = (
                np.broadcast_to(self.lon, self.time.shape) << self.lon.unit
            )
            lat: u.Quantity = (
                np.broadcast_to(self.lat, self.time.shape) << self.lat.unit
            )
            distance: Optional[u.Quantity] = (
                None
                if self.distance is None
                else np.broadcast_to(self.distance, self.time.shape)  # type: ignore
            )
            time = self.time
        elif self.time.isscalar or (self.time.size == 1):
            lon = self.lon
            lat = self.lat
            distance = self.distance
            time: Time = np.broadcast_to(self.time, self.lon.shape)  # type: ignore
        else:
            raise ValueError(
                "Either `lon` or `lat` must be a scalar, or they must have the same "
                "shape as `time`."
            )
        return self.__class__(
            lon=lon, lat=lat, distance=distance, frame=self.frame, time=time
        )

    @property
    def size(self) -> int:
        return self.broadcasted.lon.size

    @property
    def shape(self) -> Tuple[int, ...]:
        return self.broadcasted.lon.shape


class NameCoordinate(Coordinate):
    def __init__(self, name: str, time: Optional[Time] = None, /):
        self.name = name
        self.time = time

    def realize(
        self, time: Optional[Union[int, float, Array[Union[int, float]], Time]] = None
    ) -> Coordinate:
        """Get the position of a celestial body from its name.

        Parameters
        ----------
        name
            Name of the celestial body.
        obstime
            Time of observation.

        Returns
        -------
        Position (SkyCoord) of the celestial body.

        Examples
        --------
        >>> calc.coord.from_name("Sun", time.time())
        Coordinate(
            lon=<Longitude 6.20805658 rad>,
            lat=<Latitude -0.03254802 rad>,
            frame=<GCRS Frame (
                obstime=1678968349.001554,
                obsgeoloc=(-3548179.23395423, 3753814.11380175, 3731512.91152004) m,
                obsgeovel=(-273.72298624, -259.34513153, 0.62044525) m / s)>,
            time=<Time object: scale='utc' format='unix' value=1678968349.001554>)
        >>> calc.coord.from_name("Orion KL", [time.time(), time.time() + 1])
        Coordinate(
            lon=<Longitude 83.809 deg>,
            lat=<Latitude -5.372639 deg>,
            frame=<ICRS Frame>,
            time=<Time object:
                scale='utc' format='unix' value=[1.67896831e+09 1.67896831e+09]>)

        """
        time = to_astropy_type.time(time)
        if time is None:
            time = self.time

        try:
            coord = get_body(self.name, time, location=self._calc.location)
        except KeyError:
            coord = SkyCoord.from_name(self.name)
        ret = self._calc.coordinate.from_skycoord(coord)
        if (ret.time is None) and (time is not None):
            ret = ret.replicate(time=time)
        return ret


@dataclass
class ApparentAltAzCoordinate:
    az: Union[DimensionLess, u.Quantity]
    alt: Union[DimensionLess, u.Quantity]
    time: Union[DimensionLess, Time]
    unit: Optional[UnitType] = None

    def __post_init__(self) -> None:
        self.az = get_quantity(self.az, unit=self.unit)
        self.alt = get_quantity(self.alt, unit=self.unit)
        self.time = to_astropy_type.time(self.time)

    @property
    def broadcasted(self) -> "ApparentAltAzCoordinate":
        if self.time is None:
            return self

        if self.az.shape != self.alt.shape:
            raise ValueError(
                "`az` and `alt` must have the same shape, but are "
                f"{self.az.shape} and {self.alt.shape}."
            )
        elif self.az.shape == self.time.shape:
            return self

        if self.az.isscalar:
            lon: u.Quantity = np.broadcast_to(self.az, self.time.shape) << self.az.unit
            lat: u.Quantity = (
                np.broadcast_to(self.alt, self.time.shape) << self.alt.unit
            )
            time = self.time
        elif self.time.isscalar:
            lon = self.az
            lat = self.alt
            time: Time = np.broadcast_to(self.time, self.az.shape)  # type: ignore
        else:
            raise ValueError(
                "Either `lon` or `lat` must be a scalar, or they must have the same "
                "shape as `time`."
            )
        return self.__class__(az=lon, alt=lat, time=time)

    @property
    def size(self) -> int:
        return self.broadcasted.az.size

    @property
    def shape(self) -> Tuple[int, ...]:
        return self.broadcasted.alt.shape


@dataclass
class CoordinateDelta:
    d_lon: Union[DimensionLess, u.Quantity]
    d_lat: Union[DimensionLess, u.Quantity]
    frame: Union[Type[BaseCoordinateFrame], BaseCoordinateFrame, str]
    unit: Optional[UnitType] = None

    def __post_init__(self) -> None:
        """Create a coordinate delta from builtin type values."""
        self.frame = to_astropy_type.frame(self.frame)
        self.d_lon = get_quantity(self.d_lon, unit=self.unit)
        self.d_lat = get_quantity(self.d_lat, unit=self.unit)

    @property
    def broadcasted(self) -> "CoordinateDelta":
        if self.d_lon.shape != self.d_lat.shape:
            raise ValueError(
                "`d_lon` and `d_lat` must have the same shape, but are "
                f"{self.d_lon.shape} and {self.d_lat.shape}."
            )
        return self.__class__(d_lon=self.d_lon, d_lat=self.d_lat, frame=self.frame)

    @property
    def size(self) -> int:
        return self.broadcasted.d_lon.size

    @property
    def shape(self) -> Tuple[int, ...]:
        return self.broadcasted.d_lon.shape


@dataclass
class CoordCalculator:
    """Collection of basic methods for celestial coordinate calculation.

    Parameters
    ----------
    location
        Location of the telescope.
    pointing_param_path
        Path to the pointing error correction parameters. If None, pointing error
        correction won't be performed.

    Examples
    --------
    >>> calc = neclib.coordinates.CoordCalculator(config.location)

    """

    location: EarthLocation = config.location  # type: ignore
    pointing_err_file: Optional[Union[os.PathLike, str]] = None

    obswl: ClassVar[QuantityValidator] = QuantityValidator(unit="mm")
    obsfreq: ClassVar[QuantityValidator] = QuantityValidator(
        config.observation_frequency, unit="GHz"  # type: ignore
    )
    relative_humidity: ClassVar[QuantityValidator] = QuantityValidator(unit="")
    pressure: ClassVar[QuantityValidator] = QuantityValidator(unit="hPa")
    temperature: ClassVar[QuantityValidator] = QuantityValidator(unit="K")

    direct_mode: bool = False
    direct_before: bool = None

    command_group_duration_sec = 1

    @property
    def command_freq(self) -> Union[int, float]:
        return config.antenna_command_frequency  # type: ignore

    @property
    def command_offset_sec(self) -> Union[int, float]:
        return config.antenna_command_offset_sec  # type: ignore

    @property
    def pointing_err(self) -> PointingError:
        if not (self.direct_mode is self.direct_before):
            self.direct_before = self.direct_mode
            if self.pointing_err_file is None:
                logger.warning("Pointing error correction is disabled. ")
                self._pointing_err = PointingError.get_dummy()
            elif self.direct_mode:
                self._pointing_err = PointingError.get_dummy()
            else:
                self._pointing_err = PointingError.from_file(self.pointing_err_file)
        return self._pointing_err

    @property
    def altaz_kwargs(self) -> Dict[str, Any]:
        """Return keyword arguments for AltAz frame, except for ``obstime``."""
        # Check if diffraction correction is enabled.
        _diffraction_params = ("pressure", "temperature", "relative_humidity", "obswl")
        diffraction_params = {x: getattr(self, x) for x in _diffraction_params}
        not_set = [k for k, v in diffraction_params.items() if v != v]
        if len(not_set) > 0:
            logger.warning(
                f"Diffraction correction is disabled. {not_set} are not given."
            )

        # Check if obswl and obsfreq are consistent.
        obswl = None
        if self.obswl == self.obswl:  # Check if self.obswl is NaN or not.
            obswl = self.obswl
        if self.obsfreq == self.obsfreq:  # Check if self.obsfreq is NaN or not.
            _obswl = self.obsfreq.to(u.mm, equivalencies=u.spectral())
            if (obswl is not None) and (obswl != _obswl):
                raise ValueError(
                    f"obswl={obswl} and obsfreq={self.obsfreq} are inconsistent."
                )
            obswl = _obswl

        return dict(
            location=self.location,
            temperature=self.temperature.to(u.deg_C, equivalencies=u.temperature()),
            pressure=self.pressure,
            relative_humidity=self.relative_humidity,
            obswl=obswl,
        )

    @property
    def coordinate(self) -> Type[Coordinate]:
        Coordinate._calc = self
        return Coordinate

    @property
    def name_coordinate(self) -> Type[NameCoordinate]:
        NameCoordinate._calc = self
        return NameCoordinate

    coordinate_delta = CoordinateDelta
