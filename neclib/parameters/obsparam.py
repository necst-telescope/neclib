"""Convert flexibly specified observation parameters to some useful form.

.. note::

   Public API won't change, but contents such as ``translate_coordsys``,
   ``COORDINATES``, and offset calculation in ``off_point_coord`` can be moved to other
   subpackage or module, i.e. ``neclib.coordinates``?

"""

__all__ = ["ObsParams", "interval", "off_point_coord"]

from typing import Any, ClassVar, Dict, Hashable, List, Tuple, Union

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.coordinates.baseframe import BaseCoordinateFrame

from .parser import ObsParamData
from .. import units as custom_u
from ..utils import ParameterMapping, quantity2builtin

# Only those not supported by Astropy
COORDINATES = {
    "j2000": "fk5",
    "b1950": "fk4",
    "horizontal": "altaz",
}


def translate_coordsys(coordsys: str) -> str:
    return COORDINATES.get(coordsys.lower(), coordsys.lower())


class ObsParams(ObsParamData):
    r"""Observation parameter calculator.

    Parameters
    ----------
    units
        Parameter name to its unit mapping.
    **kwargs
        Parameters.

    Attributes
    ----------
    val: ParameterMapping
        Returns built-in type value if the unit is provided in ``units``.

    Examples
    --------
    >>> neclib.parameters.ObsParams.ParameterUnit = {
    ...     "deg": ["LamdaOn", "BetaOn", ...], "s": ...
    ... }
    >>> params = neclib.parameters.ObsParams.from_file("path/to/parameter.file")
    >>> params.LamdaOn
    <Angle 123.45 deg>
    >>> params.val.LamdaOn
    123.45

    """

    ParameterName: Dict[str, Union[str, List[str]]] = {
        "off_observation_interval": "off_interval",
        "hot_observation_interval": "load_interval",
        "on_point_coordinate": ["LamdaOn", "BetaOn", "COORD_SYS"],
        "offset_from_on_to_off": ["deltaLamda", "deltaBeta", "DELTA_COORD"],
        "offset_coslat_applied": "OTADEL",
        "absolute_off_point_coordinate": ["LamdaOff", "BetaOff", "COORD_SYS"],
    }
    ParameterUnit: ClassVar[
        Union[Dict[Hashable, Union[u.Unit, str]], Dict[Union[u.Unit, str], List[str]]]
    ] = {}

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.val = ParameterMapping(quantity2builtin(self, self.ParameterUnit))

    def _getitem(self, param_type: str) -> Union[Any, List[Any]]:
        keys = self.ParameterName[param_type]

        if isinstance(keys, str):
            return self.get(keys, None)
        params = [self.get(key, None) for key in keys]
        if not any([param is None for param in params]):
            return params

    def off_observation_interval(
        self, *, unit: Union[str, u.Unit], points_per_scan: int = None
    ) -> Tuple[float, str]:
        """Parse OFF observation interval.

        See Also
        --------
        interval : Implementation of this method.

        """
        return interval(
            self._getitem("off_observation_interval"),
            unit=unit,
            points_per_scan=points_per_scan,
        )

    def hot_observation_interval(
        self, *, unit: Union[str, u.Unit], points_per_scan: int = None
    ) -> Tuple[float, str]:
        """Parse HOT observation interval.

        See Also
        --------
        interval : Implementation of this method.

        """
        return interval(
            self._getitem("hot_observation_interval"),
            unit=unit,
            points_per_scan=points_per_scan,
        )

    def off_point_coord(
        self, *, unit: Union[str, u.Unit], **kwargs
    ) -> Tuple[float, float, str]:
        """Parse HOT observation interval.

        See Also
        --------
        off_point_coord : Implementation of this method.

        """

        def translate(coordinate):
            if coordinate is None:
                return
            lon, lat, coordsys = coordinate
            return lon, lat, translate_coordsys(coordsys)

        return off_point_coord(
            unit=unit,
            on_point=translate(self._getitem("on_point_coordinate")),
            offset=translate(self._getitem("offset_from_on_to_off")),
            coslat_applied=self._getitem("offset_coslat_applied"),
            absolute=translate(self._getitem("absolute_off_point_coordinate")),
            **kwargs,
        )


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
    >>> neclib.parameters.interval(Quantity("5min"), unit="s")
    300, "time"
    >>> neclib.parameters.interval(Quantity("5scan"), unit="point", points_per_scan=5)
    25, "point"

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
    ``coslat_applied``, output ``unit``). The coordinates should be given in the
    form: (longitude, latitude, coordinate frame)

    Parameters
    ----------
    on_point
        Coordinate of ON point.
    offset
        Offset from ON point to OFF point. Caution the unit, as ``Angle("0h0m1s")``
        is not equivalent to ``Angle("1arcsec")``.
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
    >>> neclib.parameters.off_point_coord(
    ...     absolute=(Angle("3h25m20s"), Angle("31d32m33s"), "fk5"),
    ...     unit="deg",
    ... )
    (51.3333, 31.5425, 'fk5')
    >>> neclib.parameters.off_point_coord(
    ...     on_point=(Angle("5h1m1s"), Angle("30d25m20s"), "galactic"),
    ...     offset=(Angle("0 0 10 hours"), Angle("20arcsec"), "fk5"),
    ...     coslat_applied=True,
    ...     unit="deg",
    ... )
    (266.6442444454571, 48.39027455272732, 'fk5')

    """
    # Indices for tuple of length 3.
    LON, LAT, COORDSYS = 0, 1, 2

    def _convert_unit(
        x: u.Quantity, y: u.Quantity, coordsys: Union[str, BaseCoordinateFrame]
    ) -> Tuple[float, float, str]:
        # Extract name of ``astropy.coordinates.baseframe.BaseCoordinateFrame``.
        # The reason ``getattr`` is used instead of ``isinstance`` or ``issubclass``
        # is either of the class or its instance can be given and handling them is
        # quite complicated.
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
