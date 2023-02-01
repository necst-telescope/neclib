from typing import Optional, Union

import astropy.units as u

from ..type_aliases import DimensionLess, UnitType


def get_quantity(
    *value: Union[DimensionLess, u.Quantity], unit: Optional[UnitType] = None
) -> u.Quantity:
    """Convert a value to astropy Quantity.

    Parameters
    ----------
    value
        The value to be converted. If multiple values are given, they should have
        equivalent dimensions.
    unit
        The unit of the value. Should be given as a keyword argument.

    Returns
    -------
    quantity
        The value converted to Quantity.

    Raises
    ------
    UnitConversionError
        If the value has incompatible dimensions.
    ValueError
        If the values have different shapes.

    Examples
    --------
    >>> neclib.core.get_quantity(1, 2, 3, unit="m")
    <Quantity [1., 2., 3.] m>
    >>> neclib.core.get_quantity(np.array([1, 2, 3]), unit="m/s")
    <Quantity [1., 2., 3.] m / s>

    """
    if len(value) == 1:
        # Don't make 1-D array when there's only one value
        return u.Quantity(value[0], unit=unit)
    return u.Quantity(value, unit=unit)
