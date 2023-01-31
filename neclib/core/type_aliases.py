from typing import Callable, Literal, Protocol, Tuple, Union, runtime_checkable

import numpy as np
from astropy.coordinates import BaseCoordinateFrame
from astropy.units import UnitBase

DimensionLess = Union[int, float, np.ndarray[Tuple[int, ...], np.dtype[np.number]]]
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


@runtime_checkable
class SupportsComparison(Protocol):
    def __eq__(self, other: object) -> bool:
        ...

    def __ne__(self, other: object) -> bool:
        ...

    def __lt__(self, other: object) -> bool:
        ...

    def __le__(self, other: object) -> bool:
        ...

    def __gt__(self, other: object) -> bool:
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
