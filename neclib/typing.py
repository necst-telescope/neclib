# flake8: noqa

__all__ = ["Literal", "PathLike", "AngleUnit"]

import os
from typing import Union


# Literal type.
try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

# PathLike type.
PathLike = Union[os.PathLike, str, bytes]

# Supported arguments alias.
AngleUnit = Literal["deg", "arcmin", "arcsec"]
