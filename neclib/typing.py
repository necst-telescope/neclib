"""Type aliases for simple type hinting."""

__all__ = ["PathLike", "AngleUnit"]

import os
from typing import Literal, Union


PathLike = Union[os.PathLike, str, bytes]
"""Alias of ``os.PathLike``, with ``str`` and ``bytes`` types combined."""

AngleUnit = Literal["deg", "arcmin", "arcsec", "rad"]
"""Literal expression of supported angular units in this package."""
