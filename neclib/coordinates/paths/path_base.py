from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Generator, Optional, Tuple, Union

import astropy.units as u

from ...core.normalization import NPArrayValidator
from ...core.types import DimensionLess

if TYPE_CHECKING:
    from ..convert import CoordCalculator

T = Union[DimensionLess, u.Quantity]


class Path(ABC):

    tight: bool
    infinite: bool
    waypoint: bool

    def __init__(self, calc: CoordCalculator, *args, **kwargs) -> None:
        self._calc = calc

    @property
    @abstractmethod
    def arguments(self) -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        ...


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
