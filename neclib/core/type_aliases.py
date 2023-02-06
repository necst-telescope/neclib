from typing import Callable, Literal, Protocol, Tuple, TypeVar, Union, runtime_checkable

import numpy as np
import numpy.typing as npt
from astropy.coordinates import BaseCoordinateFrame
from astropy.units import Quantity, UnitBase

DimensionLess = Union[int, float, npt.NDArray[np.number]]
"""Type alias for values with no physical units."""

UnitType = Union[UnitBase, str]
"""Type alias for objects that represents physical unit."""

CoordFrameType = Union[str, BaseCoordinateFrame]
"""Type alias for objects that represents coordinate frame."""

EquivalencyType = Tuple[
    UnitBase, UnitBase, Callable[[float], float], Callable[[float], float]
]
"""Type alias for unit equivalency in ``astropy.units``."""

AngleUnit = Literal["deg", "rad", "arcmin", "arcsec"]
"""Type alias for supported angular units."""

CoordinateType = Tuple[Quantity, Quantity, CoordFrameType]
"""Type alias for coordinate in (lon, lat, frame) format."""


T = TypeVar("T")


@runtime_checkable
class SupportsComparison(Protocol):
    def __eq__(self: T, other: T, /) -> bool:
        ...

    def __ne__(self: T, other: T, /) -> bool:
        ...

    def __lt__(self: T, other: T, /) -> bool:
        ...

    def __le__(self: T, other: T, /) -> bool:
        ...

    def __gt__(self: T, other: T, /) -> bool:
        ...


@runtime_checkable
class TextLike(Protocol):
    def upper(self) -> "TextLike":
        ...

    def lower(self) -> "TextLike":
        ...

    def find(self) -> int:
        ...

    def replace(self) -> "TextLike":
        ...

    def __len__(self) -> int:
        ...
