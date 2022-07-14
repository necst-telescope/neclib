"""Utility functions for physical quantity or unit handling."""

__all__ = [
    "angle_conversion_factor",
    "parse_quantity",
    "partially_convert_unit",
    "force_data_type",
    "quantity2builtin",
    "optimum_angle",
    "dAz2dx",
    "dx2dAz",
]

import math
from typing import Any, Dict, Hashable, List, Tuple, Union

import astropy.units as u

from .math_utils import frange
from ..typing import AngleUnit


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
    quantity: Union[str, u.Quantity], *, unit: Union[str, u.Unit] = None
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


def partially_convert_unit(
    quantity: u.Quantity, new_unit: Union[str, u.Unit]
) -> u.Quantity:
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
    base_units = quantity.unit.bases
    new_units = u.Unit(new_unit).bases
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
    unit: Union[
        Dict[Hashable, Union[u.Unit, str]], Dict[Union[u.Unit, str], List[str]]
    ] = {},
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


def optimum_angle(
    current: float,
    target: float,
    limits: Tuple[float, float],
    margin: float = 40.0,  # 40 deg
    threshold_allow_360deg: float = 5.0,  # 5 deg
    unit: AngleUnit = "deg",
) -> float:
    """Find optimum unwrapped angle.

    Azimuthal control of telescope should avoid:

    1. 360deg drive during observation.
        This mean you should observe around Az=-100deg, not 260deg, for telescope with
        [-270, 270]deg azimuthal operation range.
    2. Over-180deg drive to point the telescope.
        When both Az=170deg and -190deg are safe in avoiding the 360deg drive, less
        separated one is better, i.e., if the telescope is currently pointed at
        Az=10deg, you should select 170deg to save time.

    Parameters
    ----------
    current
        Current coordinate.
    target
        Target coordinate.
    limits
        Operation range of telescope drive.
    margin
        Safety margin around limits. While observations, this margin can be violated to
        avoid suspension of scan.
    threshold_allow_360deg
        If separation between current and target coordinates is smaller than this value,
        360deg drive won't occur, even if ``margin`` is violated. This parameter should
        be greater than the maximum size of a region to be mapped in 1 observation.
    unit
        Angular unit of given arguments and return value of this function.

    Notes
    -----
    This is a utility function, so there's large uncertainty where this function
    finally settle in.
    This function will be executed in high frequency, so the use of
    ``utils.parse_quantity`` is avoided.

    Examples
    --------
    >>> neclib.utils.optimum_angle(15, 200, limits=[-270, 270], margin=20, unit="deg")
    -160.0
    >>> neclib.utils.optimum_angle(15, 200, limits=[0, 360], margin=5, unit="deg")
    200.0

    """
    assert limits[0] < limits[1], "Limits should be given in ascending order."
    deg = angle_conversion_factor("deg", unit)
    turn = 360 * deg

    # Avoid 360deg drive while observation.
    if abs(target - current) < threshold_allow_360deg:
        return target

    target_candidate_min = target - turn * ((target - limits[0]) // turn)
    target_candidates = [
        angle
        for angle in frange(target_candidate_min, limits[1], turn)
        if (limits[0] + margin) < angle < (limits[1] - margin)
    ]
    if len(target_candidates) == 1:
        # If there's only 1 candidate, return it, even if >180deg motion needed.
        return target_candidates[0]
    else:
        # Avoid over-180deg drive.
        optimum = [
            angle for angle in target_candidates if abs(angle - current) <= turn / 2
        ][0]
        return optimum


def dAz2dx(
    az: Union[float, u.Quantity], el: Union[float, u.Quantity], unit: Union[u.Unit, str]
) -> float:
    az, el = list(
        map(lambda z: z.to_value(unit) if hasattr(z, "value") else z, [az, el])
    )
    rad = angle_conversion_factor(str(unit), "rad")
    return az * math.cos(el * rad)


def dx2dAz(
    x: Union[float, u.Quantity], el: Union[float, u.Quantity], unit: Union[u.Unit, str]
) -> float:
    x, el = list(map(lambda z: z.to_value(unit) if hasattr(z, "value") else z, [x, el]))
    rad = angle_conversion_factor(str(unit), "rad")
    return x / math.cos(el * rad)
