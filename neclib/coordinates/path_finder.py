__all__ = ["PathFinder", "standby_position"]

import math
import time
from typing import Callable, Generator, List, Optional, Tuple, TypeVar, Union

import astropy.units as u
import numpy as np
from astropy.coordinates import BaseCoordinateFrame

from .. import config, utils
from ..typing import Number, UnitType
from .convert import CoordCalculator

T = TypeVar("T", Number, u.Quantity)


def standby_position(
    start: Tuple[T, T],
    end: Tuple[T, T],
    *,
    margin: Optional[Union[float, int, u.Quantity]],
    unit: Optional[UnitType] = None,
) -> Tuple[u.Quantity, u.Quantity]:
    """Calculate the standby position taking into account the margin during scanning.

    Parameters
    ----------
    start
        Longitude and latitude of start point.
    end
        Longitude and latitude of end point.
    unit
        Angular unit in which longitude and latitude are given. If they are given as
        ``Quantity``, this parameter will be ignored.

    Examples
    --------
    >>> neclib.coordinates.standby_position(start=(30, 50), end=(32, 50), unit="deg")
    (<Quantity 29. deg>, <Quantity 50. deg>)

    """
    margin = utils.get_quantity(margin, unit=unit)
    start_lon, start_lat = utils.get_quantity(start[0], start[1], unit=unit)
    end_lon, end_lat = utils.get_quantity(end[0], end[1], unit=unit)

    if start_lon != end_lon and start_lat == end_lat:  # scan along longitude
        standby_lon = start_lon - margin * np.sign(end_lon - start_lon)
        standby_lat = start_lat
    elif start_lon == end_lon and start_lat != end_lat:  # scan along latitude
        standby_lon = start_lon
        standby_lat = start_lat - margin * np.sign(end_lat - start_lat)
    else:
        raise NotImplementedError(
            "Diagonal scan isn't implemented yet."
        )  # TODO: Implement.

    return (standby_lon, standby_lat)


def get_position_angle(start_lon, end_lon, start_lat, end_lat):
    if end_lon == start_lon:
        position_angle = (np.pi / 2 * u.rad) * np.sign(end_lat - start_lat)
    else:
        position_angle = np.arctan((end_lat - start_lat) / (end_lon - start_lon))
        position_angle += (np.pi if end_lon < start_lon else 0) * u.rad

    return position_angle


class PathFinder(CoordCalculator):
    """望遠鏡の軌道を計算する

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
    >>> pressure = 850 * u.hPa
    >>> temperature = 290 * u.K
    >>> humid = 0.5
    >>> obsfreq = 230 * u.GHz
    >>> finder = neclib.coordinates.PathFinder(
    ...     location, path, pressure=pressure, temperature=temperature,
    ...     relative_humidity=humid, obsfreq=obsfreq)

    """

    command_unit_duration_sec = 1

    @property
    def unit_n_cmd(self) -> int:
        return int(self.command_unit_duration_sec * config.antenna_command_frequency)

    def functional(
        self,
        lon: Callable[[float], T],
        lat: Callable[[float], T],
        frame: Union[str, BaseCoordinateFrame],
        *,
        unit: Optional[UnitType] = None,
        n_cmd: Union[int, float],
    ) -> Generator[Tuple[u.Quantity, u.Quantity, List[float]], None, None]:
        """Calculate the path of antenna movement from any function.

        Parameters
        ----------
        lon
            Function that returns longitude. The function should accept single argument;
            auxiliary variable of value between 0 and 1.
        lat
            Function that returns latitude.
        frame
            Frame in which the coordinates are given.
        unit
            Angular unit in which longitude and latitude are given. If they are given as
            ``Quantity``, this parameter will be ignored.
        n_cmd
            Number of commands. The path will be calculated supplying arithmetic
            sequence of auxiliary variable, which first term is 0, last is 1, number of
            members is ``n_cmd``.

        Returns
        -------
        Az, El, Time
            Tuple of conversion result, azimuth, elevation and time.

        Examples
        --------
        >>> def lon(x):
        ...     return 30 + x * 2
        >>> def lat(x):
        ...     return 50
        >>> path = finder.functional(lon, lat, frame="altaz", unit="deg", n_cmd=1000)
        >>> next(path)
        (<Quantity [30., 30.1, 30.2, ...] deg>, <Quantity [50., 50., 50., ...] deg>,
        [1610612736.0, 1610612736.1, 1610612736.2, ...])

        """
        start = time.time() + config.antenna_command_offset_sec
        for seq in range(math.ceil(n_cmd / self.unit_n_cmd)):
            idx = [seq * self.unit_n_cmd + j for j in range(self.unit_n_cmd)]
            param = [_idx / n_cmd for _idx in idx]
            param = list(filter(lambda x: x <= 1, param))
            idx = idx[: len(param)]
            if (seq == math.ceil(n_cmd / self.unit_n_cmd) - 1) and (param[-1] < 1):
                param.append(1)
                idx.append(idx[-1] + (param[-1] - param[-2]) * n_cmd)
            lon_for_this_seq = [lon(p) for p in param]
            lat_for_this_seq = [lat(p) for p in param]
            t_for_this_seq = [
                start
                + (seq * self.command_unit_duration_sec)
                + (i / config.antenna_command_frequency)
                for i in idx
            ]
            yield self.get_altaz(
                lon=lon_for_this_seq,
                lat=lat_for_this_seq,
                frame=frame,
                unit=unit,
                obstime=t_for_this_seq,
            )

    def linear(
        self,
        start: Tuple[T, T],
        end: Tuple[T, T],
        frame: Union[str, BaseCoordinateFrame],
        *,
        speed: Union[float, int, u.Quantity],
        unit: Optional[UnitType] = None,
    ) -> Generator[Tuple[u.Quantity, u.Quantity, List[float]], None, None]:
        """望遠鏡の直線軌道を計算する

        Parameters
        ----------
        start
            Longitude and latitude of start point.
        end
            Longitude and latitude of end point.
        frame
            Coordinate frame, in which longitude and latitude are given.
        speed
            Telescope drive speed.
        unit
            Angular unit in which longitude and latitude are given. If they are given as
            ``Quantity``, this parameter will be ignored.

        Returns
        -------
        Az, El, Time
            Tuple of calculated azimuth, elevation and time commands.

        Examples
        --------
        >>> finder.linear(
            start=(0, 0), end=(0.05, 0), frame="altaz", speed=0.5, unit=u.deg
        )
        [<Quantity [-1.47920569, -1.46920569, -1.45920569, -1.44920569, -1.43920569,
           -1.42920569] deg>, <Quantity [-1.88176239, -1.88176188, -1.88176136,
           -1.88176084, -1.88176032, -1.8817598 ] deg>, array([1.66685637e+09,
           1.66685637e+09, 1.66685637e+09, 1.66685637e+09,
           1.66685637e+09, 1.66685637e+09])]

        """
        start = utils.get_quantity(*start, unit=unit)
        end = utils.get_quantity(*end, unit=unit)
        speed = utils.get_quantity(speed, unit=end[0].unit / u.s)
        distance = ((start[0] - end[0]) ** 2 + (start[1] - end[1]) ** 2) ** 0.5
        n_cmd = (distance / speed) * (config.antenna_command_frequency * u.Hz)

        def lon(x):
            return start[0] + x * (end[0] - start[0])

        def lat(x):
            return start[1] + x * (end[1] - start[1])

        return self.functional(lon, lat, frame, unit=unit, n_cmd=float(n_cmd))

    def linear_with_acceleration(
        self,
        start: Tuple[T, T],
        end: Tuple[T, T],
        frame: Union[str, BaseCoordinateFrame],
        *,
        speed: Union[float, int, u.Quantity],
        unit: Optional[UnitType] = None,
        margin: Union[float, int, u.Quantity],
    ):
        ...

    def offset_linear(self):
        ...

    def offset_track(self):
        ...

    def track(
        self,
        lon: T,
        lat: T,
        frame: Union[str, BaseCoordinateFrame],
        *,
        unit: Optional[UnitType] = None,
    ) -> Generator[Tuple[u.Quantity, u.Quantity, List[float]], None, None]:
        while True:
            t = time.monotonic()
            yield from self.functional(
                lambda x: lon, lambda x: lat, frame, unit=unit, n_cmd=self.unit_n_cmd
            )
            time.sleep(self.command_unit_duration_sec - (time.monotonic() - t))
