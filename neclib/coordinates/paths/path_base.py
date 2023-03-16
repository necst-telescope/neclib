from __future__ import annotations

import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Generator, Optional, Tuple, Union, overload

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time

from ...core.normalization import NPArrayValidator
from ...core.types import CoordFrameType, DimensionLess, UnitType

if TYPE_CHECKING:
    from ..convert import CoordCalculator

T = Union[DimensionLess, u.Quantity]


class Path(ABC):

    tight: bool
    infinite: bool
    waypoint: bool

    def __init__(
        self, calc: CoordCalculator, *target, unit: Optional[UnitType] = None, **kwargs
    ) -> None:
        self._calc = calc

        if len(target) == 0:
            _target = None
        elif (len(target) == 1) and isinstance(target[0], str):
            _target = target[0]
        elif len(target) == 3:
            lon, lat, frame = target
            _target = self.get_skycoord(lon, lat, frame, unit=unit)  # type: ignore
        else:
            raise TypeError(
                "Invalid number of positional arguments: expected 0 (none, other "
                "arguments specify the absolute coordinate), 1 (target_name) or "
                f"3 (lon, lat, coordinate_frame), but got {len(target)}"
            )
        self._target = _target

    @property
    @abstractmethod
    def arguments(self) -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        ...

    @property
    def target_frame(self) -> Optional[CoordFrameType]:
        if self._target is None:
            return None
        elif isinstance(self._target, SkyCoord):
            frame = self._target.frame
        else:
            frame = self._calc.get_body(self._target, time.time()).frame

        if "obstime" in frame.frame_attributes:
            frame = frame.replicate_without_data(obstime=None)

        return frame

    @overload
    def get_skycoord(self, /, *, obstime: Any = None, unit: Any = None) -> None:
        ...

    @overload
    def get_skycoord(
        self, coord: SkyCoord, /, *, obstime: Any = None, unit: Any = None
    ) -> SkyCoord:
        ...

    @overload
    def get_skycoord(
        self, coord: str, /, *, obstime: Union[Time, DimensionLess], unit: Any = None
    ) -> SkyCoord:
        ...

    @overload
    def get_skycoord(
        self,
        lon: T,
        lat: T,
        frame: CoordFrameType,
        /,
        *,
        obstime: Optional[Union[Time, DimensionLess]] = None,
        unit: Optional[UnitType] = None,
    ) -> SkyCoord:
        ...

    def get_skycoord(
        self,
        *coord: Union[str, T, CoordFrameType, SkyCoord],
        obstime: Optional[Union[Time, DimensionLess]] = None,
        unit: Optional[UnitType] = None,
    ) -> Optional[SkyCoord]:
        if len(coord) == 0:
            return
        elif (len(coord) == 1) and isinstance(coord[0], SkyCoord):
            return coord[0]
        elif (len(coord) == 1) and isinstance(coord[0], str) and (obstime is not None):
            return self._calc.get_body(coord[0], obstime)
        elif len(coord) == 3:
            lon, lat, frame = coord
            return self._calc.create_skycoord(
                lon, lat, frame=frame, obstime=obstime, unit=unit
            )
        raise TypeError(f"Unexpected argument types: {type(coord)=}, {type(obstime)=}")

    @overload
    def apply_offset(
        self,
        coord: SkyCoord,
        /,
        *,
        offset: Optional[Tuple[T, T, CoordFrameType]] = None,
    ) -> SkyCoord:
        ...

    @overload
    def apply_offset(
        self,
        *coords: SkyCoord,
        offset: Optional[Tuple[T, T, CoordFrameType]] = None,
        obstime: Optional[Union[Time, DimensionLess]] = None,
        unit: Optional[UnitType] = None,
    ) -> Tuple[SkyCoord, ...]:
        ...

    def apply_offset(
        self,
        *coords: SkyCoord,
        offset: Optional[Tuple[T, T, CoordFrameType]] = None,
        obstime: Optional[Union[Time, DimensionLess]] = None,
        unit: Optional[UnitType] = None,
    ) -> Union[Tuple[SkyCoord, ...], SkyCoord]:
        if offset is None:
            return coords if len(coords) > 1 else coords[0]

        offset_applied = []
        for coord in coords:
            applied = self._calc.cartesian_offset_by(
                coord, *offset, obstime=obstime, unit=unit
            )
            offset_applied.append(applied)

        return tuple(offset_applied) if len(coords) > 1 else offset_applied[0]


@dataclass
class Index:
    time: NPArrayValidator = NPArrayValidator[float]()
    index: NPArrayValidator = NPArrayValidator[Union[int, float]]()


@dataclass
class ControlContext:
    tight: Optional[bool] = None
    """If True, the section is for observation so its accuracy should be inspected."""
    start: Optional[float] = None
    """Start time of this control section."""
    stop: Optional[float] = None
    """End time of this control section."""
    duration: Optional[float] = None
    """Time duration of this control section."""
    infinite: bool = False
    """Whether the control section is infinite hence need interruption or not."""
    waypoint: bool = False
    """Whether this is waypoint hence need some value to be sent or not."""

    @contextmanager
    def properties_modified(self, **kwargs) -> Generator[None, None, None]:
        original = {
            k: getattr(self, k) for k in kwargs if k in self.__dataclass_fields__
        }
        for k, v in kwargs.items():
            setattr(self, k, v)
        try:
            yield
        finally:
            for k, v in original.items():
                setattr(self, k, v)
