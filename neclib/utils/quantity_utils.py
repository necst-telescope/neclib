__all__ = ["angle_conversion_factor", "parse_quantity_once"]

from typing import Union
import astropy.units as u
from ..typing import AngleUnit


def angle_conversion_factor(from_: AngleUnit, to: AngleUnit) -> float:
    """Unit conversion.

    More general implementation may be realized using astropy.units, but it's ~1000
    times slower than this thus can be a bottleneck in this time critical
    calculation.

    """
    equivalents = {"deg": 1, "arcmin": 60, "arcsec": 3600}
    try:
        return equivalents[to] / equivalents[from_]
    except KeyError:
        raise ValueError(
            "Units other than than 'deg', 'arcmin' or 'arcsec' are not supported."
        )


def parse_quantity_once(
    quantity: Union[str, u.Quantity], *, unit: Union[str, u.Unit] = None
) -> u.Quantity:
    """Quantity parser with high cost and rich functionality."""
    if unit is None:
        return u.Quantity(quantity)
    else:
        return partially_convert_unit(u.Quantity(quantity), unit)


def partially_convert_unit(
    quantity: u.Quantity, new_unit: Union[str, u.Unit]
) -> u.Quantity:
    """Replace unit of given dimension."""
    base_units = quantity.unit.bases
    new_units = u.Unit(new_unit).bases
    for base in base_units:
        if not any([base.is_equivalent(new_u) for new_u in new_units]):
            new_units.append(base)
    if len(base_units) != len(new_units):
        raise ValueError(
            f"Couldn't find all equivalent units; give equivalents of {base_units}."
        )
    return quantity.decompose(bases=new_units)
