# flake8: noqa

"""Type aliases for simple scripts."""

__all__ = ["Literal", "PathLike", "AngleUnit"]

import os
from typing import Union

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

Literal = Literal
"""Alias of ``Literal``, defined in different packages as Python versions differ."""

PathLike = Union[os.PathLike, str, bytes]
"""Alias of ``os.PathLike``, with ``str`` and ``bytes`` types combined."""

AngleUnit = Literal["deg", "arcmin", "arcsec"]
"""Literal expression of supported angle units in this package."""
