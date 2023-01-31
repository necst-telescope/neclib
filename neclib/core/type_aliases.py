from typing import Tuple, Union

import numpy as np
from astropy.units import Unit

DimensionLess = Union[int, float, np.ndarray[Tuple[int, ...], np.dtype[np.number]]]
"""Type alias for values with no physical units."""

UnitType = Union[Unit, str]
"""Type alias for objects that represents physical unit."""
