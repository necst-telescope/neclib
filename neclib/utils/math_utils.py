"""Utility functions for arithmetic operations."""

__all__ = ["discretize", "counter", "ConditionChecker"]

import itertools
import math
from typing import Generator, Literal, Optional


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


def counter(
    stop: Optional[int] = None, allow_infty: bool = False
) -> Generator[int, None, None]:
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
