# flake8: noqa

# Literal type.
try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

# Supported arguments.
AngleUnit = Literal["deg", "arcmin", "arcsec"]
