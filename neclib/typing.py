"""Type aliases for simple type hinting."""

__all__ = ["PathLike", "AngleUnit"]

import os
from typing import Literal, Union

import numpy as np


PathLike = Union[os.PathLike, str]
"""Alias of ``os.PathLike``, with ``str`` type combined."""

AngleUnit = Literal["deg", "arcmin", "arcsec", "rad"]
"""Literal expression of supported angular units in this package."""

Number = Union[int, float, np.ndarray]
"""Number types."""

Boolean = Union[bool, np.bool_]
"""Boolean types."""
