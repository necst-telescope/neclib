"""Type aliases for simple type hinting."""

__all__ = ["Literal", "PathLike", "AngleUnit"]

import os
from typing import Union

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal


Literal = Literal
"""Alias of ``Literal``, defined in different packages depends on Python versions."""

PathLike = Union[os.PathLike, str, bytes]
"""Alias of ``os.PathLike``, with ``str`` and ``bytes`` types combined."""

AngleUnit = Literal["deg", "arcmin", "arcsec", "rad"]
"""Literal expression of supported angular units in this package."""
