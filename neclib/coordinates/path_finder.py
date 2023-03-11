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
            _start_idx = seq * unit_n_cmd
            _idx = [_start_idx + i for i in range(unit_n_cmd) if _start_idx + i < n_cmd]
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
            yield ApparentAltAzCoordinate(
                az=altaz.az,  # type: ignore
                el=altaz.alt,  # type: ignore
                time=_t,
                context=context,
            )

    def sequential(
        self, *section_args: Tuple[Tuple[Any, ...], Dict[str, Any]], repeat: int = 1
    ) -> CoordinateGenerator:
        last_stop = None
        counter = range(repeat) if repeat > 0 else count()

        for _ in counter:
            for args, kwargs in section_args:
                section = self.from_function(*args, **kwargs)
                for coord in section:
                    # Independent path calculators may not know when the computed
                    # command will be sent, especially when the path follows another
                    # path. They just know how long it takes to complete the commands
                    # they computed. So the time consistency is computed here, in case
                    # start and stop times are given in duration (relative time).
                    if coord.context.stop is not None:
                        last_stop = coord.context.stop
                    if coord.context.duration is not None:
                        coord.context.start = (
                            last_stop or time.time() + self.command_offset_sec
                        )
                        coord.context.stop = (
                            coord.context.start + coord.context.duration
                        )

                    yield coord

    def linear(self, *target, offset) -> CoordinateGenerator:
        ...

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
