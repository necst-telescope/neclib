__all__ = ["PathFinder", "standby_position", "CoordinateGeneratorManager"]

import math
import time as pytime
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Generator,
    Iterable,
    List,
    Literal,
    Optional,
    Tuple,
    TypeVar,
    Union,
)

import astropy.units as u
import numpy as np
from astropy.coordinates.name_resolve import NameResolveError

from .. import config, utils
from ..core.type_aliases import CoordFrameType, DimensionLess, UnitType
from .convert import CoordCalculator

T = TypeVar("T", DimensionLess, u.Quantity)


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
    controlled: bool = True
    tight: Optional[bool] = None
    """If True, the section is for observation so its accuracy should be inspected."""
    start: Optional[float] = None
    """Start time of this control section."""
    stop: Optional[float] = None
    """End time of this control section."""
    infinite: bool = False
    """Whether the control section is infinite hence need interruption or not."""
    waypoint: bool = False
    """Whether this is waypoint hence need some value to be sent or not."""

    def __bool__(self) -> bool:
        return True


CoordinateGenerator = Generator[
    Tuple[u.Quantity, u.Quantity, List[float], ControlStatus], Literal[True], None
]


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
    ) -> CoordinateGenerator:
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

    def standby(
        self,
        lon: Callable[[float], float],
        lat: Callable[[float], float],
        frame: CoordFrameType,
        *,
        at: Union[int, float] = 0,
        unit: Optional[UnitType] = None,
        time: Optional[Timer] = None,
        mode: Optional[ControlStatus] = None,
    ) -> CoordinateGenerator:
        mode = mode or ControlStatus()
        if not mode.waypoint:
            mode.infinite = True
        while True:
            yield from self.functional(
                lambda x: lon(at),
                lambda x: lat(at),
                frame=frame,
                unit=unit,
                n_cmd=self.unit_n_cmd,
                time=time,
                mode=mode,
            )

    def accelerate(
        self,
        lon: Callable[[float], T],
        lat: Callable[[float], T],
        frame: CoordFrameType,
        *,
        length: Union[int, float],
        margin: Union[int, float, u.Quantity],
        speed: Union[float, int, u.Quantity],
        unit: UnitType,
        time: Optional[Timer] = None,
        mode: Optional[ControlStatus] = None,
    ) -> CoordinateGenerator:
        time = time or Timer()
        mode = mode or ControlStatus()
        mode.infinite = False
        mode.tight = False

        margin = utils.get_quantity(margin, unit=unit)
        length = utils.get_quantity(length, unit=unit)
        speed = abs(utils.get_quantity(speed, unit=margin.unit / u.s))

        self.logger.warning(
            "Calculation involving AltAz coordinate may contain a jump of speed "
            "(~0.001deg/s) on transition from acceleration mode to linear drive, due to"
            " insufficient consideration of sidereal motion"
        )

        start_param = -margin / length
        scale = -1 / start_param

        if margin.value == 0:
            required_time = 0 * u.s
        else:
            # マージン部分の座標計算 加速度その1
            a = (speed**2) / (2 * margin)

            # マージン部分の座標計算 加速度その2
            # a_az = config.antenna_max_acceleration_az
            # a_el = config.antenna_max_acceleration_el
            # a = (a_az**2 + a_el**2) ** (1 / 2)
            required_time = ((2 * margin) / a) ** (1 / 2)
        n_cmd = required_time.to_value("s") * config.antenna_command_frequency

        def scaled(x):
            propto_accel = x**2
            return propto_accel / scale + start_param

        tracking_ok = None
        mode.waypoint = True
        for result in self.standby(
            lon, lat, frame, at=start_param, time=time, mode=mode
        ):
            tracking_ok = yield result
            if tracking_ok is not None:
                break
        mode.waypoint = False

        # Duration this drive will take (required_time) isn't taken into account, so the
        # functions `lon` and `lat` can be different from the ones used in linear path
        # calculation that will follow this. The angular error is approximately equal to
        # (sidereal motion speed * required_time).
        yield from self.functional(
            lambda x: lon(scaled(x)),
            lambda x: lat(scaled(x)),
            frame=frame,
            n_cmd=n_cmd,
            time=time,
            mode=mode,
        )

    def linear(
        self,
        start: Tuple[T, T],
        end: Tuple[T, T],
        frame: CoordFrameType,
        *,
        speed: Union[float, int, u.Quantity],
        unit: Optional[UnitType] = None,
        margin: Union[int, float, u.Quantity],
        time: Optional[Timer] = None,
        mode: Optional[ControlStatus] = None,
    ) -> CoordinateGenerator:
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
        mode = mode or ControlStatus()
        mode.infinite = False

        start = utils.get_quantity(*start, unit=unit)
        end = utils.get_quantity(*end, unit=unit)
        speed = abs(utils.get_quantity(speed, unit=f"{end.unit}/s"))
        distance = ((start - end) ** 2).sum() ** 0.5
        n_cmd = (distance / speed) * (config.antenna_command_frequency * u.Hz)

        def lon(x):
            return start[0] + x * (end[0] - start[0])

        def lat(x):
            return start[1] + x * (end[1] - start[1])

        yield from self.accelerate(
            lon,
            lat,
            frame,
            length=distance,
            margin=margin,
            speed=speed,
            unit=end.unit,
            time=time,
            mode=ControlStatus(tight=False),
        )

        mode.tight = True
        yield from self.functional(
            lon, lat, frame, unit=unit, n_cmd=n_cmd, mode=mode, time=time
        )

    def offset_linear(
        self,
        start: Tuple[T, T],
        end: Tuple[T, T],
        frame: CoordFrameType,
        *,
        reference: Tuple[T, T, CoordFrameType],
        speed: Union[float, int, u.Quantity],
        unit: Optional[UnitType] = None,
        margin: Union[int, float, u.Quantity],
        time: Optional[Timer] = None,
        mode: Optional[ControlStatus] = None,
    ) -> CoordinateGenerator:
        time = time or Timer()
        mode = mode or ControlStatus()
        mode.infinite = False

        start = utils.get_quantity(*start, unit=unit)
        end = utils.get_quantity(*end, unit=unit)
        speed = abs(utils.get_quantity(speed, unit=f"{end.unit}/s"))
        distance = ((start - end) ** 2).sum() ** 0.5
        n_cmd = (distance / speed) * (config.antenna_command_frequency * u.Hz)

        t = self.time_index(time.get(), n_cmd)
        idx = self.index(n_cmd)
        ref = self.get_skycoord(
            *reference[:2], frame=reference[2], obstime=t, unit=unit
        )
        ref = self.transform_to(ref, frame)

        def lon(x):
            ref_lon = np.interp(x, idx, ref.data.lon)
            return ref_lon + start[0] + x * (end[0] - start[0])

        def lat(x):
            ref_lat = np.interp(x, idx, ref.data.lat)
            return ref_lat + start[1] + x * (end[1] - start[1])

        yield from self.accelerate(
            lon,
            lat,
            frame,
            length=distance,
            margin=margin,
            speed=speed,
            unit=end.unit,
            time=time,
            mode=ControlStatus(tight=False),
        )

        mode.tight = True
        yield from self.functional(
            lon, lat, frame, unit=unit, n_cmd=n_cmd, time=time, mode=mode
        )

    def offset_linear_by_name(
        self,
        start: Tuple[T, T],
        end: Tuple[T, T],
        frame: CoordFrameType,
        *,
        name: str,
        speed: Union[float, int, u.Quantity],
        unit: Optional[UnitType] = None,
        margin: Union[int, float, u.Quantity],
        time: Optional[Timer] = None,
        mode: Optional[ControlStatus] = None,
    ) -> CoordinateGenerator:
        time = time or Timer()
        mode = mode or ControlStatus()
        mode.infinite = False

        start = utils.get_quantity(*start, unit=unit)
        end = utils.get_quantity(*end, unit=unit)
        speed = abs(utils.get_quantity(speed, unit=f"{end.unit}/s"))
        distance = ((start - end) ** 2).sum() ** 0.5
        n_cmd = (distance / speed) * (config.antenna_command_frequency * u.Hz)

        t = self.time_index(time.get(), n_cmd)
        idx = self.index(n_cmd)
        if frame == "altaz":
            frame = self._get_altaz_frame(t)
        try:
            ref = self.get_body(name, t)
            ref = self.transform_to(ref, frame)
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

        yield from self.accelerate(
            lon,
            lat,
            frame,
            length=distance,
            margin=margin,
            speed=speed,
            unit=end.unit,
            time=time,
            mode=ControlStatus(tight=False),
        )

        mode.tight = True
        yield from self.functional(lon, lat, frame, n_cmd=n_cmd, time=time, mode=mode)

    def track(
        self,
        lon: T,
        lat: T,
        frame: CoordFrameType,
        *,
        unit: Optional[UnitType] = None,
        time: Optional[Timer] = None,
        mode: Optional[ControlStatus] = None,
    ) -> CoordinateGenerator:
        time = time or Timer()
        mode = mode or ControlStatus()
        mode.tight = True
        if not mode.waypoint:
            mode.infinite = True
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
        mode: Optional[ControlStatus] = None,
    ) -> CoordinateGenerator:
        time = time or Timer()
        mode = mode or ControlStatus()
        mode.tight = True
        if not mode.waypoint:
            mode.infinite = True

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
        mode: Optional[ControlStatus] = None,
    ) -> CoordinateGenerator:
        time = time or Timer()
        mode = mode or ControlStatus()
        mode.tight = True
        if not mode.waypoint:
            mode.infinite = True
        offset_lon, offset_lat = utils.get_quantity(*offset[:2], unit=unit)

        def f_lon(x):
            return np.interp(x, self.unit_index, offset_applied_lon)

        def f_lat(x):
            return np.interp(x, self.unit_index, offset_applied_lat)

        while True:
            t = self.time_index(time.get())
            ref = self.get_skycoord(lon, lat, frame=frame, obstime=t, unit=unit)
            ref_in_target_frame = self.transform_to(ref, offset[2])
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
        mode: Optional[ControlStatus] = None,
    ) -> CoordinateGenerator:
        time = time or Timer()
        mode = mode or ControlStatus()
        mode.tight = True
        if not mode.waypoint:
            mode.infinite = True
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
            ref_in_target_frame = self.transform_to(ref, frame)
            offset_applied_lon = ref_in_target_frame.data.lon + offset_lon
            offset_applied_lat = ref_in_target_frame.data.lat + offset_lat

            yield from self.functional(
                lon, lat, offset[2], n_cmd=self.unit_n_cmd, time=time, mode=mode
            )


class CoordinateGeneratorManager:
    def __init__(self, generator: Optional[CoordinateGenerator] = None) -> None:
        self._generator = generator
        self._send_value = None

    def will_send(self, value: Any) -> None:
        self._send_value = value

    def __iter__(self) -> Iterable[Any]:
        return self

    def __next__(self) -> Any:
        if self._generator is None:
            self._send_value = None
            raise StopIteration("No generator attached")
        if self._send_value is None:
            return next(self._generator)
        try:
            ret = self._generator.send(self._send_value)
            self._send_value = None
            return ret
        except TypeError:
            # Keep send value once for just-started generator
            return next(self._generator)

    def attach(self, generator: CoordinateGenerator) -> None:
        self.clear()
        self._generator = generator

    def clear(self) -> None:
        if self._generator is not None:
            try:
                self._generator.close()
            except Exception:
                pass
        self._generator = None

    def get(self) -> Optional[CoordinateGenerator]:
        return self._generator
