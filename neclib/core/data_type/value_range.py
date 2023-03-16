from typing import Any, Callable, Generic, Iterable, Iterator, Optional, TypeVar

import numpy as np

from ..types import SupportsComparison

T = TypeVar("T", bound=SupportsComparison)


class ValueRange(Generic[T]):
    """Value range bound by 2 values.

    Parameters
    ----------
    lower
        Lower bound of the range. Any type with comparison support is allowed.
    upper
        Upper bound of the range. Any type with comparison support is allowed.
    strict
        If ``True``, the value exactly equals to the bound will judged to be
        not in the range.

    Examples
    --------
    >>> valid_value = neclib.ValueRange(0, 1)
    >>> 0.5 in valid_value
    True
    >>> -1 in valid_value
    False

    You can also check lexical order of strings:

    >>> valid_str = neclib.ValueRange("aaa", "bbb")
    >>> "abc" in valid_str
    True

    The lower and upper bounds can be iterated over:

    >>> _ = [print(limits) for limits in valid_value]
    aaa
    bbb

    """

    def __init__(self, lower: T, upper: T, strict: bool = False) -> None:
        try:
            if lower > upper:
                raise ValueError("Lower bound must be smaller than upper bound.")
        except TypeError:
            raise TypeError("Bounds must support comparison.")

        self.lower, self.upper = lower, upper
        self.strict = strict

    def __contains__(self, value: Any, /) -> bool:
        if self.strict:
            return self.lower < value < self.upper
        return self.lower <= value <= self.upper

    def __iter__(self) -> Iterator[T]:
        return iter((self.lower, self.upper))

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return f"{class_name}({self.lower}, {self.upper}, strict={self.strict})"

    def __eq__(self, other: Any, /) -> bool:
        if not isinstance(other, self.__class__):
            return False
        eq_limits = (self.lower == other.lower) and (self.upper == other.upper)
        return eq_limits and self.strict is other.strict

    @property
    def width(self) -> Optional[T]:
        """Width of the range.

        Examples
        --------
        >>> valid_value = neclib.ValueRange(0, 1)
        >>> valid_value.width
        1

        """
        try:
            return self.upper - self.lower  # type: ignore
        except TypeError:
            return None

    def contain_all(self, values: Iterable[Any]) -> bool:
        """Check if all values are in the range.

        Parameters
        ----------
        values
            Iterable object to be checked.

        Examples
        --------
        >>> valid_value = neclib.ValueRange(0, 1)
        >>> valid_value.contain_all([0.5, 1.6])
        False

        """
        values = np.asanyarray(values)
        if self.strict:
            ret = ((self.lower < values) & (values < self.upper)).all()
        else:
            ret = ((self.lower <= values) & (values <= self.upper)).all()
        return bool(ret)

    def contain_any(self, values: Iterable[Any]) -> bool:
        """Check if any value is in the range.

        Parameters
        ----------
        values
            Iterable object to be checked.

        Examples
        --------
        >>> valid_value = neclib.ValueRange(0, 1)
        >>> valid_value.contain_any([0.5, 1.6])
        True

        """
        values = np.asanyarray(values)
        if self.strict:
            ret = ((self.lower < values) & (values < self.upper)).any()
        else:
            ret = ((self.lower <= values) & (values <= self.upper)).any()
        return bool(ret)

    def map(self, func: Callable[[T], Any], /) -> "ValueRange":
        """Map a function to upper and lower bounds.

        Parameters
        ----------
        func
            Function to apply.

        Examples
        --------
        >>> valid_value = neclib.ValueRange(0, 1)
        >>> valid_value.map(lambda x: 10 * x)
        ValueRange(0, 10, strict=False)

        """
        return self.__class__(func(self.lower), func(self.upper), self.strict)
