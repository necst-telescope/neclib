"""Utility functions for physical quantity or unit handling."""

__all__ = [
    "angle_conversion_factor",
    "parse_quantity",
    "partially_convert_unit",
    "force_data_type",
    "quantity2builtin",
    "dAz2dx",
    "dx2dAz",
    "get_quantity",
]

import math
from typing import Any, Dict, Hashable, Optional, List, Union, overload

import astropy.units as u

from ..typing import AngleUnit, Number, UnitType


def angle_conversion_factor(original: AngleUnit, to: AngleUnit) -> float:
    """Conversion factor between angular units.

    Parameters
    ----------
    original
        Original angular unit.
    to
        Unit to convert to.

    Notes
    -----
    More general implementation may be realized using astropy.units, but it's ~1000
    times slower than this thus can be a bottleneck in time critical calculations.

    Examples
    --------
    >>> angle_deg = 1
    >>> angle_deg * neclib.utils.angle_conversion_factor("deg", "arcsec")
    3600  # arcsec

    """
    equivalents = {"deg": 1, "arcmin": 60, "arcsec": 3600, "rad": math.pi / 180}
    try:
        return equivalents[to] / equivalents[original]
    except KeyError:
        raise ValueError(
            "Units other than than 'deg', 'arcmin' or 'arcsec' are not supported."
        )


def force_data_type(az, el, unit="deg"):
    def convert_unit(param):
        if isinstance(param, u.Quantity):
            param.to(unit)
        else:
            param *= u.Unit(unit)
        return param

    az = convert_unit(az)
    el = convert_unit(el)

    return az, el


def parse_quantity(
    quantity: Union[str, u.Quantity], *, unit: Optional[UnitType] = None
) -> u.Quantity:
    """Get ``astropy.units.Quantity`` object, optionally converting units.

    Parameters
    ----------
    quantity
        ``Quantity`` object or its ``str`` expression.
    unit
        Unit(s) you want to use.

    Examples
    --------
    >>> neclib.utils.parse_quantity("3 M_sun pc^-2")
    <Quantity 3. solMass / pc2>
    >>> neclib.utils.parse_quantity("3 M_sun pc^-2", unit="kg")
    <Quantity 5.96542625e+30 kg / pc2>

    See Also
    --------
    partially_convert_unit : For unit conversion.

    """
    if unit is None:
        return u.Quantity(quantity)
    else:
        return partially_convert_unit(u.Quantity(quantity), unit)


def partially_convert_unit(quantity: u.Quantity, new_unit: UnitType) -> u.Quantity:
    """Replace unit of given dimension.

    Parameters
    ----------
    quantity
        Original ``Quantity`` object.
    new_unit
        Unit(s) to employ.

    Notes
    -----
    ``new_unit`` should be (product of) units which construct ``quantity``'s unit. If
    unit of ``quantity`` is ``J / s``, this function can employ ``erg``, but cannot
    convert to ``W``.

    Examples
    --------
    >>> quantity = u.Quantity("3 L_sun s")
    >>> neclib.utils.partially_convert_unit(quantity, "W")
    <Quantity 1.1484e+27 s W>
    >>> neclib.utils.partially_convert_unit(quantity, "W hour")
    <Quantity 3.19e+23 h W>
    >>> neclib.utils.partially_convert_unit(quantity, "J")
    ValueError: Couldn't find equivalent units; give equivalent(s) of ["s", "solLum"].

    """
    base_units = quantity.unit.bases  # type: ignore
    new_units: List[u.UnitBase] = u.Unit(new_unit).bases  # type: ignore
    for base in base_units:
        if not any([base.is_equivalent(new_u) for new_u in new_units]):
            new_units.append(base)
    if len(base_units) != len(new_units):
        raise ValueError(
            f"Couldn't find equivalent units; give equivalent(s) of {base_units}."
        )
    return quantity.decompose(bases=new_units)


def quantity2builtin(
    quantity: Dict[Hashable, u.Quantity],
    unit: Union[Dict[Hashable, Union[u.Unit, str]], Dict[UnitType, List[str]]] = {},
) -> Dict[Hashable, Union[int, float, Any]]:
    """Convert quantity to Python's built-in types.

    Parameters
    ----------
    quantity
        Dictionary of quantity objects to convert.
    unit
        Dictionary of units to employ, in either formats: ``{parameter_name: unit}``,
        ``{unit: [parameter_name]}``.

    Examples
    --------
    >>> neclib.utils.quantity2builtin(
    ...     {"c": u.Quantity("299792458m/s")}, unit={"c": "km/s"}
    ... )
    {'c': 299792.458}
    >>> neclib.utils.quantity2builtin(
    ...     {"c": u.Quantity("299792458m/s")}, unit={"km/s": ["c"]}
    ... )
    {'c': 299792.458}

    Notes
    -----
    If there are parameters not in ``unit``, the values won't be converted.

    """
    _unit = {}
    for k, v in unit.items():
        if isinstance(v, (str, u.UnitBase)):
            _unit[k] = v
        else:
            _unit.update({name: k for name in v})

    def _convert(param, unit):
        return param if (unit is None) else param.to_value(unit)

    return {key: _convert(quantity[key], _unit.get(key, None)) for key in quantity}


def dAz2dx(
    az: Union[Number, u.Quantity], el: Union[Number, u.Quantity], unit: UnitType
) -> Number:
    az, el = list(
        map(lambda z: z.to_value(unit) if isinstance(z, u.Quantity) else z, [az, el])
    )
    rad = angle_conversion_factor(str(unit), "rad")  # type: ignore
    return az * math.cos(el * rad)  # type: ignore


def dx2dAz(
    x: Union[Number, u.Quantity], el: Union[Number, u.Quantity], unit: UnitType
) -> Number:
    x, el = list(
        map(lambda z: z.to_value(unit) if isinstance(z, u.Quantity) else z, [x, el])
    )
    rad = angle_conversion_factor(str(unit), "rad")  # type: ignore
    return x / math.cos(el * rad)  # type: ignore


class _GetQuantity:
    def __init__(self, default_unit=None):
        self._default_unit = default_unit
        self._nan = u.Quantity(float("nan"), self._default_unit)

    def __set_name__(self, owner, name):
        self._name = "_" + name

    def __set__(self, instance, value):
        if isinstance(value, str):
            value = u.Quantity(value)
        elif isinstance(value, (int, float)):
            value = u.Quantity(value, self._default_unit)
        setattr(instance, self._name, value)

    def __get__(self, instance, type=None):
        if instance is None:
            return self._nan
        return getattr(instance, self._name, self._nan)


@overload
def get_quantity(*, default_unit: Optional[UnitType]) -> _GetQuantity:
    ...


@overload
def get_quantity(
    *value: Union[str, Number, u.Quantity], unit: Optional[UnitType]
) -> u.Quantity:
    ...


def get_quantity(*value, unit=None, default_unit=None):
    """Convert values to quantity.

    Attention
    ---------
    This function has multiple signatures, one is simple converter from float values to
    Quantity, the other is attribute type validator. See examples.

    Parameters
    ----------
    value
        Values to convert.
    unit
        Unit to employ.
    default_unit
        Default unit to use.

    Examples
    --------
    To use as a type converter:
    >>> neclib.utils.get_quantity(1, 2, 3, unit="m")
    <Quantity [1., 2., 3.] m>
    >>> neclib.utils.get_quantity("1m", "2m", "3m")
    <Quantity [1., 2., 3.] m>

    To use as a type validator with default conversion:
    >>> class Test:
    ...     a = neclib.utils.get_quantity(default_unit="m")
    ...     b = neclib.utils.get_quantity(default_unit="m")
    >>> test = Test()
    >>> test.a = 1
    >>> test.b = "2m"
    >>> test.a
    <Quantity 1. m>
    >>> test.b
    <Quantity 2. m>

    """
    if not value:
        return _GetQuantity(default_unit)
    unit = None if unit is None else u.Unit(unit)

    def parser(v):
        if isinstance(v, u.Quantity):
            return v if unit is None else v.to(unit)
        return u.Quantity(v, unit)

    if len(value) == 1:
        return parser(*value)
    parsed = tuple(parser(v) for v in value)
    try:
        return u.Quantity(parsed)
    except (u.UnitConversionError, TypeError, ValueError):
        return parsed
