"""Utility functions for arithmetic operations."""

__all__ = ["clip", "frange", "discretize", "counter", "ConditionChecker"]

import itertools
import math
from typing import Generator, Literal, TypeVar

import numpy as np

from ..typing import QuantityValue, SupportsComparison


T = TypeVar("T", bound=SupportsComparison)


def clip(value: T, minimum: T = None, maximum: T = None, *, absmax: T = None) -> T:
    """Limit the ``value`` to the range [``minimum``, ``maximum``].

    Parameters
    ----------
    value
        Arbitrary parameter.
    minimum
        Lower limit of ``value``.
    maximum
        Upper limit of ``value``.
    absmax
        Upper limit of absolute value of ``value``.

    Examples
    --------
    >>> neclib.utils.clip(1.2, 0, 1)
    1
    >>> neclib.utils.clip(41, 0, 100)
    41
    >>> neclib.utils.clip(-4, absmax=3)
    -3

    """
    if absmax is not None:
        minimum, maximum = -1 * abs(absmax), abs(absmax)
    if minimum > maximum:
        raise ValueError("Minimum should be less than maximum.")
    return min(max(minimum, value), maximum)


def frange(
    start: QuantityValue,
    stop: QuantityValue,
    step: QuantityValue = None,
    *,
    inclusive: bool = False,
) -> Generator[QuantityValue, None, None]:
    """Float version of built-in ``range``, with support for including stop value.

    Parameters
    ----------
    start
        First value to be yielded.
    stop
        Last value to be yielded never exceeds this limit.
    step
        Difference between successive 2 values to be yielded.
    inclusive
        If ``True``, ``stop`` value can be yielded when ``stop - start`` is multiple of
        ``step``.

    Notes
    -----
    Because of floating point overflow, errors may appear when ``print``-ing the result,
    but it's the same as almost equivalent function ``numpy.arange``.

    Examples
    --------
    >>> list(neclib.utils.frange(0, 1, 0.2))
    [0, 0.2, 0.4, 0.6, 0.8]
    >>> list(neclib.utils.frange(0, 1, 0.2, inclusive=True))
    [0, 0.2, 0.4, 0.6, 0.8, 1]

    """
    if step is None:
        unity = 1 * getattr(start, "unit", 1)
        step = unity
    if inclusive:
        num = -1 * np.ceil((start - stop) / step) + 1
        # HACK: ``-1 * ceil(x) + 1`` is ceiling function, but if ``x`` is integer,
        # return ``ceil(x) + 1``, so no ``x`` satisfies ``quasi_ceil(x) == x``.
    else:
        num = np.ceil((stop - start) / step)

    for i in range(int(num)):
        yield start + (step * i)


def discretize(
    value: float,
    start: float = 0.0,
    step: float = 1.0,
    *,
    method: Literal["nearest", "ceil", "floor"] = "nearest",
) -> float:
    """Convert ``value`` to nearest element of arithmetic sequence.

    Parameters
    ----------
    value
        Parameter to discretize.
    start
        First element of element of arithmetic sequence.
    step
        Difference between the consecutive 2 elements of the sequence.
    method
        Discretizing method.

    Examples
    --------
    >>> neclib.utils.discretize(3.141592)
    3
    >>> neclib.utils.discretize(3.141592, step=10)
    0
    >>> neclib.utils.discretize(3.141592, method="ceil")
    4
    >>> neclib.utils.discretize(3.141592, start=2.5, step=0.7)
    3.2

    """
    discretizer = {"nearest": round, "ceil": math.ceil, "floor": math.floor}
    return discretizer[method]((value - start) / step) * step + start


def counter(stop: int = None, allow_infty: bool = False) -> Generator[int, None, None]:
    """Generate integers from 0 to ``stop``.

    Parameters
    ----------
    stop
        Number of yielded values.
    allow_infty
        If ``True``, the counter counts up to infinity. Listing such object will cause
        memory leak, so use caution.

    Examples
    --------
    >>> list(neclib.utils.counter(5))
    [0, 1, 2, 3, 4]
    >>> list(neclib.utils.counter())
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, ...]  # -> memory leak

    """
    if (stop is None) and (not allow_infty):
        raise ValueError("Specify ``stop`` value, unless ``allow_infty`` is set True.")
    elif stop is None:
        yield from itertools.count()
    elif stop < 0:
        raise ValueError("Stop value should be non-negative.")
    else:
        yield from range(stop)


class ConditionChecker:
    def __init__(self, sequential: int = 1, reset_on_failure: bool = True):
        self.__sequential = sequential
        self.__reset_on_failure = reset_on_failure
        self.__count = 0

    def check(self, condition: bool):
        self.__count += 1 if condition else 0
        if self.__reset_on_failure:
            self.__count *= int(condition)
        return self.__count >= self.__sequential
