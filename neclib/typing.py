"""Type aliases for simple type hinting."""

__all__ = ["PathLike", "AngleUnit"]

import os
from typing import Callable, Literal, Protocol, Tuple, Union, runtime_checkable

import astropy.units as u
import numpy as np
from astropy.coordinates import BaseCoordinateFrame


PathLike = Union[os.PathLike, str]
"""Alias of ``os.PathLike``, with ``str`` type combined."""

AngleUnit = Literal["deg", "arcmin", "arcsec", "rad"]
"""Literal expression of supported angular units in this package."""

Number = Union[int, float, np.ndarray]
"""Dimensionless value types."""
ValueType = Number
"""Dimensionless value types."""

Boolean = Union[bool, np.bool_]
"""Boolean types."""
BoolType = Boolean
"""Boolean types."""

Unit = Union[str, u.UnitBase]
"""Unit of physical quantity."""
UnitType = Unit
"""Unit of physical quantity."""

CoordFrameType = Union[str, BaseCoordinateFrame]
"""Coordinate frame type."""

QuantityValue = Union[Number, u.Quantity]
"""Physical quantity or primitive type with unit separately specified."""

EquivalencyType = Tuple[
    u.UnitBase, u.UnitBase, Callable[[float], float], Callable[[float], float]
]
"""Type expression for unit equivalency in astropy.units."""


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


@runtime_checkable
class SupportsComparison(Protocol):
    def __eq__(self, other: "SupportsComparison") -> bool:
        ...

    def __ne__(self, other: "SupportsComparison") -> bool:
        ...

    def __lt__(self, other: "SupportsComparison") -> bool:
        ...

    def __le__(self, other: "SupportsComparison") -> bool:
        ...

    def __gt__(self, other: "SupportsComparison") -> bool:
        ...

    def __ge__(self, other: "SupportsComparison") -> bool:
        ...
