import os
import time
from typing import Any, ClassVar, Dict, Optional, Type, TypeVar, Union, overload

import astropy.units as u
import numpy as np
from astropy.coordinates import BaseCoordinateFrame, EarthLocation, SkyCoord, get_body
from astropy.coordinates.erfa_astrom import ErfaAstromInterpolator, erfa_astrom
from astropy.time import Time

from ..core import config, get_logger, math
from ..core.normalization import QuantityValidator, get_quantity
from ..core.types import CoordFrameType, DimensionLess, UnitType
from .frame import parse_frame
from .pointing_error import PointingError

CoordinateLike = TypeVar("CoordinateLike", SkyCoord, BaseCoordinateFrame)


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

    obswl = QuantityValidator(unit="mm")
    obsfreq = QuantityValidator(
        config.observation_frequency, unit="GHz"  # type: ignore
    )
    relative_humidity = QuantityValidator(unit="")
    pressure = QuantityValidator(unit="hPa")
    temperature = QuantityValidator(unit="deg_C")

    command_group_duration_sec: ClassVar[Union[int, float]] = 1

    def __init__(
        self,
        location: EarthLocation,
        pointing_param_path: Optional[Union[os.PathLike, str]] = None,
    ) -> None:
        self.logger = get_logger(self.__class__.__name__, throttle_duration_sec=60)
        self.location = location
        self.command_freq: Union[int, float] = config.antenna_command_frequency
        self.command_offset_sec: Union[int, float] = config.antenna_command_offset_sec

        if pointing_param_path is None:
            self.logger.warning("Pointing error correction is disabled. ")
            self.pointing_err = PointingError.get_dummy()
        else:
            self.pointing_err = PointingError.from_file(pointing_param_path)

    def get_body(self, name: str, obstime: Union[Time, DimensionLess]) -> SkyCoord:
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
        >>> calc.get_body("Sun", time.time())
        <SkyCoord (GCRS: obstime=1678164787.532903:
            (ra, dec, distance) in (deg, deg, AU)
            (347.13736866, -5.51345537, 0.9921115)>
        >>> calc.get_body("Orion KL", [time.time(), time.time() + 1])
        <SkyCoord (ICRS): (ra, dec) in deg
            [(83.809, -5.372639), (83.809, -5.372639)]>

        """
        obstime = self._normalize(obstime=obstime)
        try:
            coord = get_body(name, obstime, self.location)
        except KeyError:
            coord = SkyCoord.from_name(name, frame="icrs")
        return np.broadcast_to(coord, obstime.shape)  # type: ignore

    def _get_obstime(
        self,
        start: Optional[Union[Time, DimensionLess]] = None,
        n: Optional[Union[int, float]] = None,
    ) -> Time:
        _start: DimensionLess
        if start is None:
            _start = time.time() + self.command_offset_sec
        elif isinstance(start, Time):
            _start = start.unix
        else:
            _start = start

        n = self.command_freq if n is None else n

        # Due to floating point error, the number of elements can be slightly different
        # from the expected value `n`. So the output of `np.arange` is sliced.
        times = np.arange(
            _start,
            _start + n / self.command_freq,  # type: ignore
            1 / self.command_freq,
        )[:n]
        return Time(times, format="unix")

    @property
    def altaz_kwargs(self) -> Dict[str, Any]:
        """Return keyword arguments for AltAz frame, except for ``obstime``."""
        # Check if diffraction correction is enabled.
        _diffraction_params = ("pressure", "temperature", "relative_humidity", "obswl")
        diffraction_params = {x: getattr(self, x) for x in _diffraction_params}
        not_set = [k for k, v in diffraction_params.items() if v != v]
        if len(not_set) > 0:
            self.logger.warning(
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

    @overload
    def _normalize(self, *, obstime: None = None) -> None:
        ...

    @overload
    def _normalize(self, *, obstime: Union[Time, DimensionLess]) -> Time:
        ...

    @overload
    def _normalize(
        self, *, frame: CoordFrameType
    ) -> Union[BaseCoordinateFrame, Type[BaseCoordinateFrame]]:
        ...

    def _normalize(
        self,
        *,
        obstime: Optional[Union[Time, DimensionLess]] = None,
        frame: Optional[CoordFrameType] = None,
    ) -> Any:
        """Convert and normalize physical parameter objects to AstroPy types."""
        if obstime is not None:
            if isinstance(obstime, Time):
                return obstime
            return Time(obstime, format="unix")
        if frame is not None:
            if isinstance(frame, str):
                frame = parse_frame(frame)
            return frame

    def transform_to(
        self,
        coord: SkyCoord,
        new_frame: CoordFrameType,
        *,
        obstime: Optional[Union[Time, DimensionLess]] = None,
    ) -> SkyCoord:
        """Transform celestial coordinate between any frames.

        Parameters
        ----------
        coord
            The coordinates to convert.
        new_frame
            The frame to convert to.
        obstime
            Time of observation. The different ``obstime`` is attached to ``coord``,
            this method converts the frame considering the time difference.

        Returns
        -------
        The converted coordinates.

        """
        new_frame = self._normalize(frame=new_frame)
        obstime = self._normalize(obstime=obstime)

        if (
            ("obstime" in coord.frame.frame_attributes)
            and (coord.obstime is None)
            and (obstime is None)
        ):
            raise ValueError(
                f"Time-dependent coordinate with no obstime is ambiguous: {coord}"
            )

        if ("obstime" in coord.frame.frame_attributes) and (coord.obstime is None):
            # If obstime is not attached to the original `coord`, attach it assuming
            # the `obstime` given as argument also applies to the original coordinate.
            frame = coord.frame.replicate_without_data(obstime=obstime)
            coord = self.create_skycoord(coord.data, frame=frame)

        if "obstime" in new_frame.frame_attributes:
            _obstime: Time
            if obstime is not None:
                _obstime = obstime
            elif coord.obstime is not None:
                _obstime = coord.obstime  # type: ignore
            elif new_frame.obstime is not None:  # type: ignore
                _obstime = new_frame.obstime  # type: ignore
            else:
                raise ValueError(
                    "Time information should be attached to `coord` or `new_frame` or "
                    "given as argument `obstime` for the conversion involving AltAz "
                    "frame."
                )
            coord = self._broadcast_coordinate(coord, _obstime)

            kw = dict(obstime=_obstime)
            kw.update(self.altaz_kwargs)
            kw = {k: v for k, v in kw.items() if k in new_frame.frame_attributes}
            if isinstance(new_frame, BaseCoordinateFrame):
                # If the frame is already instantiated, replicate and assign parameters.
                new_frame = new_frame.replicate_without_data(**kw)
            else:
                # If the frame is not instantiated, just instantiate with parameters.
                new_frame = new_frame(**kw)

            if coord.name == "altaz":
                # In AltAz to AltAz conversion, no coordinate transformation should be
                # performed. This disables the sidereal motion tracking of coordinate in
                # AltAz frame.
                coord = self._broadcast_coordinate(coord, new_frame.obstime)
                return SkyCoord(
                    coord.az,
                    coord.alt,
                    frame=new_frame,
                )

        # Interpolate astrometric parameters, for better performance.
        # https://docs.astropy.org/en/stable/coordinates/index.html#improving-performance-for-arrays-of-obstime
        with erfa_astrom.set(ErfaAstromInterpolator(300 * u.s)):
            return coord.transform_to(new_frame)

    def to_apparent_altaz(self, coord: SkyCoord) -> SkyCoord:
        """Convert celestial coordinate in any frame to telescope frame.

        This method converts the given ``coord`` to AltAz frame, taking into account
        the pointing error correction and the sidereal motion. Observation time is
        automatically set, based on command frequency and time offset of commands
        specified in NECST configuration.

        Parameters
        ----------
        coord : SkyCoord
            The coordinates to convert.

        Returns
        -------
        The converted (AltAz) coordinates. The observation time starts from
        ``time.time() + config.command_offset_sec`` and ends at
        ``time.time() + config.command_offset_sec + cls.command_group_duration_sec``
        with the frequency ``config.antenna_command_frequency``.

        Notes
        -----
        If the coord provided ``coord`` is already in the AltAz frame, this method
        simply returns the broadcasted version of it. This is because coordinates in
        AltAz frame should have already accounted for the sidereal motion. Therefore, no
        additional tracking calculations are necessary, only pointing error correction.

        """
        obstime: Time
        if coord.obstime is None:
            # If no obstime is attached, generate it.
            obstime = self._get_obstime(n=len(coord))
        elif (coord.obstime.shape == coord.shape) and (coord.ndim > 0):
            # If all obstime is specified, just use it, except if it is a scalar. Single
            # obstime would be to eliminate ambiguity of time-dependent coordinate, so
            # it must be broadcasted, not just used as is.
            obstime = coord.obstime  # type: ignore
        elif (coord.ndim == 0) and (coord.obstime.ndim != 0):
            # If obstime is fully specified but coordinate is a scalar, broadcast it.
            obstime = coord.obstime  # type: ignore
        else:
            # If obstime is specified but not for all elements of given `coord`,
            # generate the time sequence starting from the obstime.
            obstime = self._get_obstime(start=coord.obstime, n=len(coord))  # type: ignore

        broadcasted_coord = self._broadcast_coordinate(coord, obstime)

        altaz_coord = self.transform_to(broadcasted_coord, "altaz", obstime=obstime)

        # Apply pointing error correction.
        apparent = self.pointing_err.refracted_to_apparent(
            altaz_coord.az, altaz_coord.alt, unit="deg"  # type: ignore
        )
        return SkyCoord(*apparent, frame="altaz", obstime=obstime, **self.altaz_kwargs)

    def cartesian_offset_by(
        self,
        coord: SkyCoord,
        d_lon: Union[DimensionLess, u.Quantity],
        d_lat: Union[DimensionLess, u.Quantity],
        d_frame: CoordFrameType,
        *,
        unit: Optional[UnitType] = None,
        obstime: Optional[Union[Time, DimensionLess]] = None,
    ) -> SkyCoord:
        d_frame = self._normalize(frame=d_frame)
        obstime = self._normalize(obstime=obstime)
        d_lon, d_lat = get_quantity(d_lon, d_lat, unit=unit)

        coord_in_target_frame = self.transform_to(coord, d_frame, obstime=obstime)

        return SkyCoord(
            coord_in_target_frame.data.lon + d_lon,  # type: ignore
            coord_in_target_frame.data.lat + d_lat,  # type: ignore
            frame=coord_in_target_frame.frame,
        )

    def create_skycoord(self, *args, **kwargs) -> SkyCoord:
        """Create a SkyCoord object from flexibly parsed argument values and types.

        This method is a wrapper of ``astropy.coordinates.SkyCoord`` that automatically
        normalizes the frame and obstime arguments, if they are given.

        Parameters
        ----------
        *args
            Positional arguments to be passed to ``astropy.coordinates.SkyCoord``.
        **kwargs
            Keyword arguments to be passed to ``astropy.coordinates.SkyCoord``.

        Returns
        -------
        The created SkyCoord object.

        Examples
        --------
        >>> calc.create_skycoord(0 * u.deg, 0 * u.deg, frame="icrs")
        <SkyCoord (ICRS): (ra, dec) in deg
            (0., 0.)>

        """
        if "frame" in kwargs:
            kwargs["frame"] = self._normalize(frame=kwargs["frame"])
        if "obstime" in kwargs:
            kwargs["obstime"] = self._normalize(obstime=kwargs["obstime"])
        if ("unit" in kwargs) and (kwargs["unit"] is None):
            kwargs.pop("unit")

        kwargs.update(self.altaz_kwargs)
        if isinstance(kwargs.get("frame", None), BaseCoordinateFrame):
            frame: BaseCoordinateFrame = kwargs["frame"]  # type: ignore
            kw = {key: getattr(kwargs["frame"], key) for key in frame.frame_attributes}
            conflicts = {}
            for key, v in frame.frame_attributes.items():
                frame_attr = kw[key]

                if key not in kwargs:
                    continue
                args_param = kwargs[key]

                if (
                    np.bool_(frame_attr == v.default).all()
                    or np.bool_(frame_attr == args_param).all()
                ):
                    kw.update({key: args_param})
                    kwargs.pop(key)
                else:
                    conflicts[key] = dict(Argument=args_param, FrameInstance=frame_attr)
                    kwargs.pop(key)

            if len(conflicts) > 0:
                self.logger.warning(
                    f"Frame instance has attributes {conflicts.keys()} set, but "
                    "conflicting values are given in argument. Former takes precedence."
                )

            args = tuple(
                self._broadcast_coordinate(x, kw.get("obstime", None)) for x in args
            )
            kwargs["frame"] = frame.replicate_without_data(**kw)

        return SkyCoord(*args, **kwargs)

    def _broadcast_coordinate(
        self, coord: CoordinateLike, obstime: Optional[Time] = None
    ) -> CoordinateLike:
        if (obstime is None) or (obstime.ndim == 0):
            return coord

        if coord.shape == obstime.shape:
            # If the shape of obstime is the same as that of coord, no need to convert
            # them.
            return coord
        elif coord.ndim == 0:
            # If coord is a scalar, simply broadcast it to the shape of obstime.
            return np.broadcast_to(coord, obstime.shape)  # type: ignore
        elif (coord.shape == obstime.shape[:-1]) or (obstime.ndim == 1):
            # If obstime has one more dimension than coord, that should be time axis.
            # If obstime has just 1 dimension, it is also assumed to be time axis.
            # In those cases, broadcast the coordinate to append the time dimension.
            return np.broadcast_to(
                coord[..., None], (*coord.shape, obstime.shape[-1])  # type: ignore
            )
        else:
            raise ValueError(f"Unexpected shape: {coord.shape=}, {obstime.shape=}")
