from typing import Any, Optional, Union

import astropy.units as u

from ..types import Array, UnitType


def get_quantity(
    *value: Union[int, float, Array[Union[int, float]], u.Quantity],
    unit: Optional[UnitType] = None
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


class QuantityValidator:
    """Type validator, to force some instance variables to be Quantity."""

    # For details on validator descriptor design, see:
    # https://docs.python.org/3/howto/descriptor.html#validator-class

    def __init__(
        self, default: Union[int, float, u.Quantity] = float("nan"), *, unit: str = ""
    ) -> None:
        self.default = u.Quantity(default, unit=unit)
        self.unit = unit

    def __set_name__(self, owner: Any, name: str) -> None:
        self.private_name = "_" + name

    def __get__(self, instance: Any, owner: Any) -> u.Quantity:
        if instance is None:
            return self.default
        return getattr(instance, self.private_name, self.default)

    def __set__(self, instance: Any, value: Union[int, float, u.Quantity]) -> None:
        if not isinstance(value, u.Quantity):
            value = u.Quantity(value, self.unit)
        setattr(instance, self.private_name, value)
