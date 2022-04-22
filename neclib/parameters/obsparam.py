__all__ = ["interval", "off_point_coord"]

from typing import Tuple, Union

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.coordinates.baseframe import BaseCoordinateFrame

from .. import units as custom_u


def interval(
    quantity: u.Quantity, *, unit: Union[str, u.Unit], points_per_scan: int = None
) -> Tuple[float, str]:
    """Parse interval.

    Parameters
    ----------
    quantity
        Input value to be parsed.
    unit
        Unit in which return value is given.
    points_per_scan
        Number of observation points per 1 scan line.

    Examples
    --------
    >>> interval(Quantity("5min"), "s")
    300
    >>> interval(Quantity("5scan"), "point", 5)
    25

    """
    if quantity.unit.is_equivalent("second"):
        return quantity.to_value(unit), "time"
    elif quantity.unit is u.Unit(unit):
        return quantity.value, str(unit)

    if points_per_scan is None:
        return quantity.to_value(unit), str(unit)
    converted = quantity.to_value(
        unit, equivalencies=custom_u.scan_to_point_equivalency(points_per_scan)
    )
    return converted, str(unit)


def off_point_coord(
    *,
    unit: Union[str, u.Unit],
    on_point: Tuple[u.Quantity, u.Quantity, Union[str, BaseCoordinateFrame]] = None,
    offset: Tuple[u.Quantity, u.Quantity, Union[str, BaseCoordinateFrame]] = None,
    coslat_applied: bool = None,
    absolute: Tuple[u.Quantity, u.Quantity, Union[str, BaseCoordinateFrame]] = None,
    **kwargs,
) -> Tuple[float, float, str]:
    """Parse OFF observation coordinate.

    Give (``absolute`` coordinate of OFF point, output ``unit``) or (coordinate of
    ``on_point``, ``offset`` from the ON point, if the offset value has
    ``coslat_applied``, output ``unit``). The coordinates should be given in the form:
    (longitude, latitude, coordinate frame)

    Parameters
    ----------
    on_point
        Coordinate of ON point.
    offset
        Offset from ON point to OFF point. Caution the unit, as ``Angle("0h0m1s")`` is
        not equivalent to ``Angle("1arcsec")``.
    coslat_applied
        If ``False``, longitude of ``offset`` will be divided by cos(latitude).
    absolute
        Absolute coordinate of OFF point.
    unit
        Unit in which return value is given.
    **kwargs
        Keyword arguments to ``SkyCoord``, will be passed to coordinate frame class
        such as AltAz; location, obstime, obswl, etc.

    Examples
    --------
    >>> off_point_coord(
    ...     absolute=(Angle("3h25m20s"), Angle("31d32m33s"), "fk5"),
    ...     unit="deg",
    ... )
    (51.3333, 31.5425, "fk5")
    >>> off_point_coord(
    ...     on_point=(,, ""),
    ...     offset=(,, ""),
    ...     coslat_applied=True,
    ...     unit="deg",
    ... )
    (,, "")

    """
    # Indexes for tuple of length 3.
    LON, LAT, COORDSYS = 0, 1, 2

    def _convert_unit(
        x: u.Quantity, y: u.Quantity, coordsys: Union[str, BaseCoordinateFrame]
    ) -> Tuple[float, float, str]:
        # Extract name of ``astropy.coordinates.baseframe.BaseCoordinateFrame``.
        # The reason ``getattr`` is used instead of ``isinstance`` or ``issubclass`` is
        # either of the class or its instance can be given and handling them is quite
        # complicated.
        coordsys = getattr(coordsys, "name", coordsys)
        return x.to_value(unit), y.to_value(unit), coordsys.lower()

    if (absolute is not None) and (offset is None):
        return _convert_unit(*absolute)

    if (absolute is None) and (offset is not None):
        on_coord = (
            SkyCoord(on_point[LON], on_point[LAT], frame=on_point[COORDSYS], **kwargs)
            .transform_to(offset[COORDSYS].lower())
            .data
        )
        if not isinstance(coslat_applied, bool):
            raise TypeError("Explicitly give ``coslat_applied`` or not.")
        if not coslat_applied:
            offset = (
                offset[LON] / np.cos(on_coord.lat),
                offset[LAT],
                offset[COORDSYS],
            )
        return _convert_unit(
            on_coord.lon + offset[LON], on_coord.lat + offset[LAT], offset[COORDSYS]
        )

    raise ValueError(
        "Coordinate to calculate is ambiguous."
        "Give either of ``absolute`` or ``offset``, not both."
    )
