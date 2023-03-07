import os
import time
from typing import Any, ClassVar, Optional, Type, Union, overload

import astropy.units as u
import numpy as np
from astropy.coordinates import (
    AltAz,
    BaseCoordinateFrame,
    EarthLocation,
    SkyCoord,
    get_body,
)
from astropy.coordinates.erfa_astrom import ErfaAstromInterpolator, erfa_astrom
from astropy.time import Time

from ..core import config, get_logger, math
from ..core.normalization import QuantityValidator
from ..core.types import CoordFrameType, DimensionLess
from .frame import parse_frame
from .pointing_error import PointingError


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
            self.pointing_err = PointingError()  # type: ignore
        else:
            self.pointing_err = PointingError.from_file(pointing_param_path)

    def get_body(self, name: str, obstime: Union[Time, DimensionLess]) -> SkyCoord:
        if not isinstance(obstime, Time):
            obstime = Time(obstime, format="unix")
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
        times = math.frange(
            _start,
            _start + n / self.command_freq,  # type: ignore
            1 / self.command_freq,
        )
        return Time(times, format="unix")

    @property
    def altaz_kwargs(self) -> dict[str, Any]:
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

        Returns
        -------
        The converted coordinates.

        """
        new_frame = self._normalize(frame=new_frame)

        if (coord.name == "altaz") and (coord.obstime is None):
            raise ValueError(f"AltAz coordinate with no obstime is ambiguous: {coord}")

        if new_frame.name == "altaz":  # type: ignore
            if obstime is not None:
                _obstime = self._normalize(obstime=obstime)
            elif coord.obstime is not None:
                _obstime = coord.obstime
            elif new_frame.obstime is not None:  # type: ignore
                _obstime = new_frame.obstime  # type: ignore
            else:
                raise ValueError(
                    "Time information should be attached to `coord` or `new_frame` or "
                    "given as argument `obstime` for the conversion involving AltAz "
                    "frame."
                )
            new_frame = AltAz(**self.altaz_kwargs, obstime=_obstime)

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
        If the given ``coord`` is already in AltAz frame, this method just returns
        the broadcasted version of it. This is because coordinates in AltAz frame should
        already have taken into account the sidereal motion, so no additional correction
        is needed.

        """
        obstime: Time
        if coord.obstime is None:
            # If no obstime is attached, generate it.
            obstime = self._get_obstime()
        elif (coord.obstime.shape == coord.shape) and (coord.ndim > 0):
            # If all obstime is specified, just use it, except if it is a scalar. Single
            # obstime would be to eliminate ambiguity of time-dependent coordinate, so
            # it must be broadcasted, not just used as is.
            obstime = coord.obstime  # type: ignore
        else:
            # If obstime is not specified for all coordinates, broadcast it.
            obstime = self._get_obstime(start=coord.obstime)  # type: ignore

        if coord.shape == obstime.shape:
            # If the shape of obstime is the same as that of coord, no need to convert
            # them.
            broadcasted_coord = coord
        elif coord.ndim == 0:
            # If coord is a scalar, simply broadcast it to the shape of obstime.
            broadcasted_coord = np.broadcast_to(coord, obstime.shape)  # type: ignore
        elif (coord.shape == obstime.shape[:-1]) or (obstime.ndim == 1):
            # If obstime has one more dimension than coord, that should be time axis.
            # If obstime has just 1 dimension, it is also assumed to be time axis.
            # In those cases, broadcast the coordinate to append the time dimension.
            broadcasted_coord = np.broadcast_to(
                coord[..., None], (*coord.shape, obstime.shape[-1])  # type: ignore
            )
        else:
            raise ValueError(f"Unexpected shape: {coord.shape=}, {obstime.shape=}")

        altaz_coord = self.transform_to(broadcasted_coord, "altaz", obstime=obstime)

        # Apply pointing error correction.
        apparent = self.pointing_err.refracted_to_apparent(
            altaz_coord.az, altaz_coord.alt, unit="deg"  # type: ignore
        )
        return SkyCoord(*apparent, frame="altaz", obstime=obstime, **self.altaz_kwargs)

    def cartesian_offset_by(
        self,
        coord: SkyCoord,
        d_lon: u.Quantity,
        d_lat: u.Quantity,
        d_frame: CoordFrameType,
        obstime: Optional[Union[Time, DimensionLess]] = None,
    ) -> SkyCoord:
        d_frame = self._normalize(frame=d_frame)
        obstime = self._normalize(obstime=obstime)

        coord_in_target_frame = self.transform_to(coord, d_frame, obstime=obstime)

        return SkyCoord(
            coord_in_target_frame.data.lon + d_lon,  # type: ignore
            coord_in_target_frame.data.lat + d_lat,  # type: ignore
            frame=coord_in_target_frame.frame,
        )
