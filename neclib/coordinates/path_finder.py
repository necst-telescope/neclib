__all__ = ["PathFinder", "standby_position"]

import math
import time as pytime
from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional, Tuple, TypeVar, Union

import astropy.units as u
import numpy as np
from astropy.coordinates.name_resolve import NameResolveError

from .. import config, utils
from ..typing import CoordFrameType, Number, UnitType
from .convert import CoordCalculator

T = TypeVar("T", Number, u.Quantity)


def standby_position(
    start: Tuple[T, T],
    end: Tuple[T, T],
    *,
    margin: Union[float, int, u.Quantity],
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
    start = utils.get_quantity(*start, unit=unit)
    end = utils.get_quantity(*end, unit=unit)
    return CoordCalculator.get_extended(start, end, length=margin)


def get_position_angle(start_lon, end_lon, start_lat, end_lat):
    return CoordCalculator.get_position_angle(
        (start_lon, end_lon), (start_lat, end_lat)
    )


class Timer:
    def __init__(self):
        self.start = pytime.time()
        self.target = self.start

    def set_offset(self, offset) -> None:
        if offset != float(offset):
            raise TypeError(f"Cannot parse offset {offset} as float value")
        self.target += float(offset)

    def get(self) -> float:
        return self.target

    def __bool__(self) -> bool:
        return True


@dataclass
class ControlStatus:
    controlled: bool
    tight: bool
    """Whether the control section is for observation or not."""
    start: Optional[float] = None
    """Start time of this control section."""
    stop: Optional[float] = None
    """End time of this control section."""


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
        """Number of commands to be calculated in ``self.command_unit_duration_sec``."""
        return int(self.command_unit_duration_sec * config.antenna_command_frequency)

    @property
    def unit_index(self) -> List[float]:
        return self.index()

    def index(self, n_cmd: Optional[Union[float, int]] = None) -> List[float]:
        if n_cmd is None:
            n_cmd = self.unit_n_cmd
        idx = [i / n_cmd for i in range(math.floor(n_cmd))]
        if n_cmd != math.floor(n_cmd):
            idx.append(n_cmd)
        return idx

    def time_index(
        self, start_time: float, n_cmd: Optional[Union[float, int]] = None
    ) -> List[float]:
        if n_cmd is None:
            n_cmd = self.unit_n_cmd
        start_time += config.antenna_command_offset_sec
        command_freq = config.antenna_command_frequency
        time = [start_time + i / command_freq for i in range(math.floor(n_cmd))]
        if n_cmd != math.floor(n_cmd):
            time.append(start_time + n_cmd / (command_freq - 1))
        return time

    def functional(
        self,
        lon: Callable[[float], T],
        lat: Callable[[float], T],
        frame: CoordFrameType,
        *,
        unit: Optional[UnitType] = None,
        n_cmd: Union[int, float],
        mode: ControlStatus,
        time: Optional[Timer] = None,
    ) -> Iterable[Tuple[u.Quantity, u.Quantity, List[float], ControlStatus]]:
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
        time
            Start time manager. If ``None``, current time will be used. No consideration
            for ``antenna_command_offset_sec`` is required.

        Returns
        -------
        Az, El, Time, ControlStatus
            Tuple of conversion result, azimuth, elevation, time and type information of
            the control section.

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
        time = time or Timer()
        start = time.get() + config.antenna_command_offset_sec
        time.set_offset(n_cmd / config.antenna_command_frequency)

        mode.start = start
        mode.stop = time.get() + config.antenna_command_offset_sec

        unit_n_cmd = self.unit_n_cmd

        for seq in range(math.ceil(n_cmd / unit_n_cmd)):
            idx = [seq * unit_n_cmd + i for i in range(unit_n_cmd)]
            param = [_idx / n_cmd for _idx in idx if _idx <= n_cmd]
            idx = idx[: len(param)]
            if (seq == math.ceil(n_cmd / unit_n_cmd) - 1) and (param[-1] < 1):
                param.append(1)
                idx.append(idx[-1] + (param[-1] - param[-2]) * n_cmd)

            t_for_this_seq = [start + i / config.antenna_command_frequency for i in idx]
            lon_for_this_seq = [lon(p) for p in param]
            lat_for_this_seq = [lat(p) for p in param]

            yield *self.get_altaz(
                lon=lon_for_this_seq,
                lat=lat_for_this_seq,
                frame=frame,
                unit=unit,
                obstime=t_for_this_seq,
            ), mode

    def linear(
        self,
        start: Tuple[T, T],
        end: Tuple[T, T],
        frame: CoordFrameType,
        *,
        speed: Union[float, int, u.Quantity],
        unit: Optional[UnitType] = None,
        time: Optional[Timer] = None,
        mode: ControlStatus = ControlStatus(controlled=True, tight=True),
    ) -> Iterable[Tuple[u.Quantity, u.Quantity, List[float], ControlStatus]]:
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
        time = time or Timer()

        start = utils.get_quantity(*start, unit=unit)
        end = utils.get_quantity(*end, unit=unit)
        speed = utils.get_quantity(speed, unit=f"{end.unit}/s")
        distance = ((start - end) ** 2).sum() ** 0.5
        n_cmd = (distance / speed) * (config.antenna_command_frequency * u.Hz)

        def lon(x):
            return start[0] + x * (end[0] - start[0])

        def lat(x):
            return start[1] + x * (end[1] - start[1])

        yield from self.functional(
            lon, lat, frame, unit=unit, n_cmd=n_cmd, mode=mode, time=time
        )

    def accelerate_to(
        self,
        start: Tuple[T, T],
        end: Tuple[T, T],
        frame: CoordFrameType,
        *,
        speed: Union[float, int, u.Quantity],
        unit: Optional[UnitType] = None,
        margin: Union[int, float, u.Quantity],
        time: Optional[Timer] = None,
        mode: ControlStatus = ControlStatus(controlled=True, tight=False),
    ) -> Iterable[Tuple[u.Quantity, u.Quantity, List[float], ControlStatus]]:
        time = time or Timer()
        margin = utils.get_quantity(margin, unit=unit)
        _margin_start = self.get_extended(start, end, length=margin)
        margin_start = utils.get_quantity(*_margin_start, unit=unit)
        margin_end = utils.get_quantity(*start, unit=unit)
        margin = utils.get_quantity(margin, unit=unit)
        speed = utils.get_quantity(speed, unit=margin.unit / u.s)

        position_angle = self.get_position_angle(margin_start, margin_end)

        # マージン部分の座標計算 加速度その1
        a = (speed**2) / (2 * margin)

        # マージン部分の座標計算 加速度その2
        # a_az = config.antenna_max_acceleration_az
        # a_el = config.antenna_max_acceleration_el
        # a = (a_az**2 + a_el**2) ** (1 / 2)

        required_time = ((2 * margin) / a) ** (1 / 2)
        n_cmd = required_time.to_value("s") * config.antenna_command_frequency
        a_lon, a_lat = a * np.cos(position_angle), a * np.sin(position_angle)

        def lon(x):
            t = x * required_time
            return margin_start[0] + a_lon * t**2 / 2

        def lat(x):
            t = x * required_time
            return margin_start[1] + a_lat * t**2 / 2

        time = time or Timer()
        yield from self.functional(
            lon, lat, frame, unit=unit, n_cmd=n_cmd, time=time, mode=mode
        )

    def linear_with_acceleration(
        self,
        start: Tuple[T, T],
        end: Tuple[T, T],
        frame: CoordFrameType,
        *,
        speed: Union[float, int, u.Quantity],
        unit: Optional[UnitType] = None,
        margin: Union[float, int, u.Quantity],
        time: Optional[Timer] = None,
    ) -> Iterable[Tuple[u.Quantity, u.Quantity, List[float], ControlStatus]]:
        time = time or Timer()
        yield from self.accelerate_to(
            start, end, frame, speed=speed, unit=unit, margin=margin, time=time
        )
        yield from self.linear(start, end, frame, speed=speed, unit=unit, time=time)

    def offset_linear(
        self,
        start: Tuple[T, T],
        end: Tuple[T, T],
        frame: CoordFrameType,
        *,
        reference: Tuple[T, T, CoordFrameType],
        speed: Union[float, int, u.Quantity],
        unit: Optional[UnitType] = None,
        time: Optional[Timer] = None,
        mode: ControlStatus = ControlStatus(controlled=True, tight=True),
    ) -> Iterable[Tuple[u.Quantity, u.Quantity, List[float], ControlStatus]]:
        time = time or Timer()

        start = utils.get_quantity(*start, unit=unit)
        end = utils.get_quantity(*end, unit=unit)
        speed = utils.get_quantity(speed, unit=f"{end.unit}/s")
        distance = ((start - end) ** 2).sum() ** 0.5
        n_cmd = (distance / speed) * (config.antenna_command_frequency * u.Hz)

        t = self.time_index(time.get(), n_cmd)
        idx = self.index(n_cmd)
        ref = self.get_skycoord(
            *reference[:2], frame=reference[2], obstime=t, unit=unit
        ).transform_to(frame)

        def lon(x):
            ref_lon = np.interp(x, idx, ref.data.lon)
            return ref_lon + start[0] + x * (end[0] - start[0])

        def lat(x):
            ref_lat = np.interp(x, idx, ref.data.lat)
            return ref_lat + start[1] + x * (end[1] - start[1])

        yield from self.functional(
            lon, lat, frame, unit=unit, n_cmd=n_cmd, time=time, mode=mode
        )

    def offset_linear_with_acceleration(
        self,
        start: Tuple[T, T],
        end: Tuple[T, T],
        frame: CoordFrameType,
        *,
        reference: Tuple[T, T, CoordFrameType],
        speed: Union[float, int, u.Quantity],
        unit: Optional[UnitType] = None,
        margin: Union[float, int, u.Quantity],
        time: Optional[Timer] = None,
        mode: ControlStatus = ControlStatus(controlled=True, tight=True),
    ) -> Iterable[Tuple[u.Quantity, u.Quantity, List[float], ControlStatus]]:
        raise NotImplementedError

    def offset_linear_by_name(
        self,
        start: Tuple[T, T],
        end: Tuple[T, T],
        frame: CoordFrameType,
        *,
        name: str,
        speed: Union[float, int, u.Quantity],
        unit: Optional[UnitType] = None,
        time: Optional[Timer] = None,
        mode: ControlStatus = ControlStatus(controlled=True, tight=True),
    ) -> Iterable[Tuple[u.Quantity, u.Quantity, List[float], ControlStatus]]:
        time = time or Timer()

        start = utils.get_quantity(*start, unit=unit)
        end = utils.get_quantity(*end, unit=unit)
        speed = utils.get_quantity(speed, unit=f"{end.unit}/s")
        distance = ((start - end) ** 2).sum() ** 0.5
        n_cmd = (distance / speed) * (config.antenna_command_frequency * u.Hz)

        t = self.time_index(time.get(), n_cmd)
        idx = self.index(n_cmd)
        if frame == "altaz":
            frame = self._get_altaz_frame(t)
        try:
            ref = self.get_body(name, t).transform_to(frame)
        except NameResolveError:
            self.logger.error(f"Cannot resolve {name!r}")
            return f"Cannot resolve {name!r}"

        def lon(x):
            ref_lon = ref.data.lon
            ref_lon = np.interp(x, idx, ref_lon) if ref_lon.size > 1 else ref_lon
            return ref_lon + start[0] + x * (end[0] - start[0])

        def lat(x):
            ref_lat = ref.data.lat
            ref_lat = np.interp(x, idx, ref_lat) if ref_lat.size > 1 else ref_lat
            return ref_lat + start[1] + x * (end[1] - start[1])

        yield from self.functional(lon, lat, frame, n_cmd=n_cmd, time=time, mode=mode)

    def offset_linear_by_name_with_acceleration(
        self,
        start: Tuple[T, T],
        end: Tuple[T, T],
        frame: CoordFrameType,
        *,
        name: str,
        speed: Union[float, int, u.Quantity],
        unit: Optional[UnitType] = None,
        margin: Union[float, int, u.Quantity],
        time: Optional[Timer] = None,
        mode: ControlStatus = ControlStatus(controlled=True, tight=True),
    ) -> Iterable[Tuple[u.Quantity, u.Quantity, List[float], ControlStatus]]:
        raise NotImplementedError

    def track(
        self,
        lon: T,
        lat: T,
        frame: CoordFrameType,
        *,
        unit: Optional[UnitType] = None,
        time: Optional[Timer] = None,
        mode: ControlStatus = ControlStatus(controlled=True, tight=True),
    ) -> Iterable[Tuple[u.Quantity, u.Quantity, List[float], ControlStatus]]:
        time = time or Timer()
        while True:
            yield from self.functional(
                lambda x: lon,
                lambda x: lat,
                frame,
                unit=unit,
                n_cmd=self.unit_n_cmd,
                time=time,
                mode=mode,
            )

    def track_by_name(
        self,
        name: str,
        *,
        time: Optional[Timer] = None,
        mode: ControlStatus = ControlStatus(controlled=True, tight=True),
    ) -> Iterable[Tuple[u.Quantity, u.Quantity, List[float], ControlStatus]]:
        time = time or Timer()

        def lon(x):
            coord_data = coord.data.lon
            if coord_data.size == 1:
                return coord_data
            return np.interp(x, self.unit_index, coord_data)

        def lat(x):
            coord_data = coord.data.lat
            if coord_data.size == 1:
                return coord_data
            return np.interp(x, self.unit_index, coord_data)

        while True:
            start_time = time.get()
            t = self.time_index(start_time)
            try:
                coord = self.get_body(name, t)
            except NameResolveError:
                self.logger.error(f"Cannot resolve {name!r}")
                return f"Cannot resolve {name!r}"

            yield from self.functional(
                lon, lat, coord.frame.name, n_cmd=self.unit_n_cmd, time=time, mode=mode
            )

    def track_with_offset(
        self,
        lon: T,
        lat: T,
        frame: CoordFrameType,
        offset: Tuple[T, T, CoordFrameType],
        *,
        unit: Optional[UnitType] = None,
        time: Optional[Timer] = None,
        mode: ControlStatus = ControlStatus(controlled=True, tight=True),
    ) -> Iterable[Tuple[u.Quantity, u.Quantity, List[float], ControlStatus]]:
        time = time or Timer()
        offset_lon, offset_lat = utils.get_quantity(*offset[:2], unit=unit)

        def f_lon(x):
            return np.interp(x, self.unit_index, offset_applied_lon)

        def f_lat(x):
            return np.interp(x, self.unit_index, offset_applied_lat)

        while True:
            t = self.time_index(time.get())
            ref = self.get_skycoord(lon, lat, frame=frame, obstime=t, unit=unit)
            ref_in_target_frame = ref.transform_to(offset[2])
            offset_applied_lon = ref_in_target_frame.data.lon + offset_lon
            offset_applied_lat = ref_in_target_frame.data.lat + offset_lat
            yield from self.functional(
                f_lon,
                f_lat,
                offset[2],
                unit=unit,
                n_cmd=self.unit_n_cmd,
                time=time,
                mode=mode,
            )

    def track_by_name_with_offset(
        self,
        name: str,
        offset: Tuple[T, T, CoordFrameType],
        *,
        unit: Optional[UnitType] = None,
        time: Optional[Timer] = None,
        mode: ControlStatus = ControlStatus(controlled=True, tight=True),
    ) -> Iterable[Tuple[u.Quantity, u.Quantity, List[float], ControlStatus]]:
        time = time or Timer()
        offset_lon, offset_lat = utils.get_quantity(*offset[:2], unit=unit)

        def lon(x):
            return np.interp(x, self.unit_index, offset_applied_lon)

        def lat(x):
            return np.interp(x, self.unit_index, offset_applied_lat)

        while True:
            start_time = time.get()
            t = self.time_index(start_time)
            try:
                ref = self.get_body(name, t)
            except NameResolveError:
                self.logger.error(f"Cannot resolve {name!r}")
                return f"Cannot resolve {name!r}"

            frame = offset[2] if offset[2] != "altaz" else self._get_altaz_frame(t)
            ref_in_target_frame = ref.transform_to(frame)
            offset_applied_lon = ref_in_target_frame.data.lon + offset_lon
            offset_applied_lat = ref_in_target_frame.data.lat + offset_lat

            yield from self.functional(
                lon, lat, offset[2], n_cmd=self.unit_n_cmd, time=time, mode=mode
            )
