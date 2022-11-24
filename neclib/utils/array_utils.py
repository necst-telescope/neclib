__all__ = ["linear_sequence"]

from typing import TypeVar, Union, overload

import astropy.units as u
import numpy as np

from ..typing import Number

T = TypeVar("T", Number, u.Quantity)


@overload
def linear_sequence(
    start: Union[int, float], stop: Union[int, float], num: int
) -> np.ndarray:
    ...


@overload
def linear_sequence(start: u.Quantity, stop: u.Quantity, num: int) -> u.Quantity:
    ...


def linear_sequence(start: T, step: T, num: int) -> T:
    """Similar to `numpy.linspace`, but unknown terminal value."""
    start, step = np.asanyarray(start), np.asanyarray(step)
    return np.linspace(start, start + step * (num - 1), num)
