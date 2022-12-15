__all__ = ["PathFinder", "standby_position"]

import math
import time
from typing import List, Optional, Tuple, TypeVar, Union

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
    margin = config.antenna_scan_margin
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

    def _linear(
        self,
        start: Tuple[T, T],
        end: Tuple[T, T],
        frame: Union[str, BaseCoordinateFrame],
        *,
        speed: Union[float, int, u.Quantity],
        unit: Optional[UnitType] = None,
        start_time: Union[float, int],
    ) -> Tuple[u.Quantity, u.Quantity, List[float]]:
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
        >>> finder._linear(
            start=(0, 0), end=(0.05, 0), frame="altaz", speed=0.5, unit=u.deg
        )
        [<Quantity [-1.47920569, -1.46920569, -1.45920569, -1.44920569, -1.43920569,
           -1.42920569] deg>, <Quantity [-1.88176239, -1.88176188, -1.88176136,
           -1.88176084, -1.88176032, -1.8817598 ] deg>, array([1.66685637e+09,
           1.66685637e+09, 1.66685637e+09, 1.66685637e+09,
           1.66685637e+09, 1.66685637e+09])]

        """

        start_lon, start_lat = utils.get_quantity(*start, unit=unit)
        end_lon, end_lat = utils.get_quantity(*end, unit=unit)
        speed = utils.get_quantity(abs(speed), unit=start_lon.unit / u.second)

        cmd_freq = config.antenna_command_frequency * u.Hz

        position_angle = get_position_angle(start_lon, end_lon, start_lat, end_lat)

        speed_lon = speed * np.cos(position_angle)
        speed_lat = speed * np.sin(position_angle)
        step_lon = speed_lon / cmd_freq
        step_lat = speed_lat / cmd_freq
        required_time = (
            (start_lon - end_lon) ** 2 + (start_lat - end_lat) ** 2
        ) ** 0.5 / speed
        n_cmd = math.ceil(required_time * cmd_freq) + 1

        offset: float = config.antenna_command_offset_sec
        lon = list(utils.linear_sequence(start_lon, step_lon, n_cmd))
        lat = list(utils.linear_sequence(start_lat, step_lat, n_cmd))
        if len(lon) != len(lat):
            lon = lon[: len(lat)] if len(lon) > len(lat) else lon
            lat = lat[: len(lon)] if len(lat) > len(lon) else lat
        t = [start_time + offset + i / cmd_freq.to_value("Hz") for i in range(n_cmd)]

        az, el, _ = self.get_altaz(
            lon=lon, lat=lat, frame=frame, unit=unit, obstime=t  # type: ignore
        )
        return (az, el, t)

    def linear(
        self,
        start: Tuple[T, T],
        end: Tuple[T, T],
        frame: Union[str, BaseCoordinateFrame],
        *,
        speed: Union[float, int, u.Quantity],
        unit: Optional[UnitType] = None,
        margin: T,
    ) -> Tuple[u.Quantity, u.Quantity, List[float]]:
        """望遠鏡の軌道を加速度を考慮しながら計算する

        Parameters
        ----------
        start
            Longitude and latitude of start point with margin.
        end
            Longitude and latitude of end point.
        frame
            Coordinate frame, in which longitude and latitude are given.
        speed
            Telescope drive speed.
        unit
            Angular unit in which longitude and latitude are given. If they are given as
            ``Quantity``, this parameter will be ignored.

        margin
            Value read from config.toml.

        Returns
        -------
        Az, El, Time
            Tuple of calculated azimuth, elevation and time commands.

        Examples
        --------
        >>> finder.linear(
            start=(0, 0),
            end=(0.05, 0),
            frame="altaz",
            speed=0.5,
            unit=u.deg,
            margin=margin
        )
        [<Quantity [-1.47920569, -1.46920569, -1.45920569, -1.44920569, -1.43920569,
           -1.42920569] deg>, <Quantity [-1.88176239, -1.88176188, -1.88176136,
           -1.88176084, -1.88176032, -1.8817598 ] deg>, array([1.66685637e+09,
           1.66685637e+09, 1.66685637e+09, 1.66685637e+09,
           1.66685637e+09, 1.66685637e+09])]

        """

        start_time = time.time()
        margin_start, margin_end = standby_position(start, end, unit=unit), start

        start_lon, start_lat = margin_start
        end_lon, end_lat = margin_end
        final_lon, final_lat = end
        speed = utils.get_quantity(abs(speed), unit=start_lon.unit / u.second)

        position_angle = get_position_angle(start_lon, end_lon, start_lat, end_lat)
        cmd_freq = config.antenna_command_frequency * u.Hz
        offset: float = config.antenna_command_offset_sec

        # マージン部分の座標計算 加速度その1
        a = (speed**2) / (2 * margin)

        # マージン部分の座標計算 加速度その2
        # a_az = config.antenna_max_acceleration_az
        # a_el = config.antenna_max_acceleration_el
        # a = (a_az**2 + a_el**2) ** (1 / 2)

        required_time = ((2 * margin) / a) ** (1 / 2)
        n_cmd = math.ceil(required_time * cmd_freq) + 1
        t = [start_time + offset + i / cmd_freq.to_value("Hz") for i in range(n_cmd)]
        dt = [_t - (start_time + offset) for _t in t] * u.s

        r = a * dt**2 / 2
        lon = start_lon + r * np.cos(position_angle)
        lat = start_lat + r * np.sin(position_angle)

        if len(lon) != len(lat):
            lon = lon[: len(lat)] if len(lon) > len(lat) else lon
            lat = lat[: len(lon)] if len(lat) > len(lon) else lat

        # リニア部分の座標計算
        lon_linear, lat_linear, t_linear = self._linear(
            start=(end_lon, end_lat),
            end=(final_lon, final_lat),
            frame=frame,
            speed=speed,
            unit=unit,
            start_time=t[-1] - offset,
        )

        # マージン部分の座標にリニア部分の座標を結合
        lon = np.r_[lon, lon_linear]
        lat = np.r_[lat, lat_linear]
        t.extend(t_linear)

        az, el, _ = self.get_altaz(
            lon=lon, lat=lat, frame=frame, unit=unit, obstime=t  # type: ignore
        )

        return (az, el, t)
