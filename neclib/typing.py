"""Type aliases for simple type hinting."""

__all__ = ["PathLike", "AngleUnit"]

import os
from typing import Literal, Protocol, Union, runtime_checkable

import astropy.units as u
import numpy as np


PathLike = Union[os.PathLike, str]
"""Alias of ``os.PathLike``, with ``str`` type combined."""

AngleUnit = Literal["deg", "arcmin", "arcsec", "rad"]
"""Literal expression of supported angular units in this package."""

Number = Union[int, float, np.ndarray]
"""Number types."""

Boolean = Union[bool, np.bool_]
"""Boolean types."""

Unit = Union[str, u.Unit]
"""Unit of physical quantity."""

QuantityValue = Union[Number, u.Quantity]
"""Physical quantity or primitive type with unit separately specified."""


@runtime_checkable
class TextLike(Protocol):
    def upper(self):
        ...

    def lower(self):
        ...

    def find(self):
        ...

    def replace(self):
        ...


@runtime_checkable
class SupportsComparison(Protocol):
    def __eq__(self, other):
        ...

    def __ne__(self, other):
        ...

    def __lt__(self, other):
        ...

    def __le__(self, other):
        ...

    def __gt__(self, other):
        ...

    def __ge__(self, other):
        ...
