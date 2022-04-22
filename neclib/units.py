"""

Notes
-----
Executing ``u.Unit("scan")`` without importing this module will fail.
To use the units defined here, please import (contents of) this module, even if the
contents don't explicitly appear in your script.

"""

__all__ = ["scan", "point", "scan_to_point_equivalency"]

from typing import Callable, List, Tuple

import astropy.units as u


EquivalencyType = Tuple[
    u.Unit, u.Unit, Callable[[float], float], Callable[[float], float]
]

scan = u.def_unit("scan")
"""Custom unit to handle number of scan lines."""

point = u.def_unit("point")
"""Custom unit to handle number of pointing positions."""

# Enable use of the units in parsing it like ``u.Unit('scan')``, or other astropy
# functions e.g. ``scan.find_equivalent_units()``
u.add_enabled_units([scan, point])


def scan_to_point_equivalency(points_per_scan: int) -> List[EquivalencyType]:
    return [(scan, point, lambda x: points_per_scan * x, lambda x: x / points_per_scan)]
