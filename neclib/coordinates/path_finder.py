import math
import time
from dataclasses import dataclass
from itertools import count
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    overload,
)

import astropy.units as u

from ..core.types import CoordFrameType, DimensionLess, UnitType
from . import paths
from .convert import CoordCalculator


@dataclass
class ApparentAltAzCoordinate:
    az: u.Quantity
    """Azimuth angle."""
    el: u.Quantity
    """Elevation angle."""
    time: List[float]
    """Time for each coordinate."""
    context: paths.ControlContext
    """Metadata of the control section this coordinate object is a part of."""


T = TypeVar("T", bound=Union[DimensionLess, u.Quantity])
CoordinateGenerator = Generator[ApparentAltAzCoordinate, Literal[True], None]


class PathFinder(CoordCalculator):
    @overload
    def from_function(
        self,
        lon: Callable[[paths.Index], T],
        lat: Callable[[paths.Index], T],
        frame: CoordFrameType,
        /,
        *,
        unit: Optional[UnitType] = None,
        n_cmd: Union[int, float],
        context: paths.ControlContext,
    ) -> CoordinateGenerator:
        ...

    @overload
    def from_function(
        self,
        lon_lat: Callable[[paths.Index], Tuple[T, T]],
        frame: CoordFrameType,
        /,
        *,
        unit: Optional[UnitType] = None,
        n_cmd: Union[int, float],
        context: paths.ControlContext,
    ) -> CoordinateGenerator:
        ...

    def from_function(
        self,
        *coord: Union[
            Callable[[paths.Index], T],
            Callable[[paths.Index], Tuple[T, T]],
            CoordFrameType,
        ],
        unit: Optional[UnitType] = None,
        n_cmd: Union[int, float],
        context: paths.ControlContext,
    ) -> CoordinateGenerator:
        """Generate coordinate commands from arbitrary function."""
        if len(coord) == 3:
            lon, lat, frame = coord

            def lon_lat_func(idx: paths.Index) -> Tuple[T, T]:
                return lon(idx), lat(idx)  # type: ignore

        elif len(coord) == 2:
            lon_lat_func, frame = coord  # type: ignore
        else:
            raise TypeError(
                "Invalid number of positional arguments: expected 2 ("
                "func(idx)->(lon, lat) and coordinate_frame) or 3 (for func1(idx)->lon,"
                f" func2(idx)->lat and coordinate_frame), but got {len(coord)}"
            )

        unit_n_cmd = int(self.command_group_duration_sec * self.command_freq)
        if context.start is None:
            context.start = time.time() + self.command_offset_sec
        if context.stop is None:
            context.stop = context.start + n_cmd / self.command_freq

        for seq in range(math.ceil(n_cmd / unit_n_cmd)):
            start_idx = seq * unit_n_cmd
            _idx = [start_idx + i for i in range(unit_n_cmd) if start_idx + i <= n_cmd]
            _t = [context.start + i / self.command_freq for i in _idx]
            idx = paths.Index(time=_t, index=_idx)

            lon_for_this_seq, lat_for_this_seq = lon_lat_func(idx)
            _coord = self.create_skycoord(
                lon_for_this_seq,
                lat_for_this_seq,
                frame=frame,
                unit=unit,
                obstime=idx.time,
            )
            altaz = self.to_apparent_altaz(_coord)
            sent = yield ApparentAltAzCoordinate(
                az=altaz.az,  # type: ignore
                el=altaz.alt,  # type: ignore
                time=_t,
                context=context,
            )
            if (sent is not None) and context.waypoint:
                context.stop = idx.time[-1]
                break

    def sequential(
        self,
        *section_args: Tuple[Sequence[Any], Dict[str, Any]],
        repeat: Union[int, Sequence[int]] = 1,
    ) -> CoordinateGenerator:
        if isinstance(repeat, int):
            counter = [range(repeat) if repeat > 0 else count()] * len(section_args)
        else:
            counter = [range(n) if n > 0 else count() for n in repeat]

        last_stop = None
        to_break = False

        for c, (args, kwargs) in zip(counter, section_args):
            for _ in c:
                context: paths.ControlContext = kwargs["context"]
                # Independent path calculators may not know when the computed command
                # will be sent, especially when the path follows another path. They just
                # know how long it takes to complete the commands they computed. So the
                # time consistency is computed here.
                if context.duration is not None:
                    context.start = last_stop or time.time() + self.command_offset_sec
                    context.stop = context.start + context.duration
                last_stop = context.stop

                section = self.from_function(*args, **kwargs)
                for coord in section:
                    sent = yield coord
                    if (sent is not None) and coord.context.waypoint:
                        to_break = True
                        context.stop = last_stop = coord.time[-1]

                if to_break:
                    to_break = False
                    break

    def linear(
        self,
        *target: Union[DimensionLess, u.Quantity, str, CoordFrameType],
        unit: Optional[UnitType] = None,
        start: Tuple[T, T],
        stop: Tuple[T, T],
        scan_frame: CoordFrameType,
        speed: T,
        margin: Optional[T] = None,
        offset: Optional[Tuple[T, T, CoordFrameType]] = None,
    ) -> CoordinateGenerator:
        args = (self, *target)
        kwargs = dict(
            unit=unit,
            start=start,
            stop=stop,
            scan_frame=scan_frame,
            speed=speed,
            margin=margin,
            offset=offset,
        )
        path1 = paths.Standby(*args, **kwargs)  # type: ignore
        path2 = paths.Accelerate(*args, **kwargs)  # type: ignore
        path3 = paths.Linear(*args, **kwargs)  # type: ignore
        arguments1 = path1.arguments
        arguments2 = path2.arguments
        arguments3 = path3.arguments

        yield from self.sequential(
            arguments1, arguments2, arguments3, repeat=[-1, 1, 1]
        )

    def track(
        self,
        *target: Union[DimensionLess, u.Quantity, str, CoordFrameType],
        unit: Optional[UnitType] = None,
        offset: Optional[Tuple[T, T, CoordFrameType]] = None,
        **ctx_kw: Any,
    ) -> CoordinateGenerator:
        path = paths.Track(self, *target, unit=unit, offset=offset, **ctx_kw)
        arguments = path.arguments
        yield from self.sequential(arguments, repeat=-1)
