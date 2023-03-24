from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, Any, Dict, Generator, Optional, Tuple, Union

import astropy.units as u
from astropy.coordinates import BaseCoordinateFrame

from ...core.normalization import NPArrayValidator
from ...core.types import CoordFrameType, DimensionLess, UnitType

if TYPE_CHECKING:
    from ..convert import CoordCalculator, Coordinate

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
            _target = calc.name_coordinate(target[0])
        elif len(target) == 3:
            lon, lat, frame = target
            _target = calc.coordinate(lon=lon, lat=lat, frame=frame, unit=unit)
        else:
            raise TypeError(
                "Invalid number of positional arguments: expected 0 (none, other "
                "arguments specify the absolute coordinate), 1 (target_name) or "
                f"3 (lon, lat, coordinate_frame), but got {len(target)}"
            )
        self._target: Optional[Coordinate] = _target

    @property
    @abstractmethod
    def arguments(self) -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        ...

    @property
    def target_frame(self) -> Optional[CoordFrameType]:
        if self._offset is not None:
            return self._offset.frame

        if self._target is None:
            return None
        else:
            import time

            target = (
                self._target.realize(time=time.time())  # type: ignore
                if hasattr(self._target, "realize")
                else self._target
            )
            frame = target.frame

        if isinstance(frame, BaseCoordinateFrame):
            return frame.replicate_without_data()
        else:
            return frame


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

    def update(self, other: ControlContext, **kwargs: Any) -> None:
        for k in fields(self):
            v = kwargs.get(k.name, getattr(other, k.name))
            setattr(self, k.name, v)
