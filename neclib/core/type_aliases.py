from typing import Callable, Tuple, Union

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
