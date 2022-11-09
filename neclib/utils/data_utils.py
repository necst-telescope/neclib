"""Utility functions for data structure handling."""

__all__ = ["ParameterList", "AzElData", "ParameterMapping", "ValueRange", "toCamelCase"]

import re
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Generic,
    Hashable,
    Iterable,
    Iterator,
    Literal,
    Optional,
    TypeVar,
)

import numpy as np

from ..typing import SupportsComparison


class ParameterList(list):
    """List, specialized in parameter storing.

    Parameters
    ----------
    value
        Iterable object to be converted to ParameterList.

    Examples
    --------
    >>> neclib.utils.ParameterList([0, 0])
    ParameterList([0, 0])
    >>> neclib.utils.ParameterList(range(5))
    ParameterList([0, 1, 2, 3, 4])

    """

    def __init__(self, value: Iterable = []):
        super().__init__(value)

    @classmethod
    def new(cls, length: int, initvalue: Any = np.nan) -> "ParameterList":
        """Create new ParameterList instance filled with initial value.

        Parameters
        ----------
        length
            Length of ``ParameterList`` to be created.
        initvalue
            Initial value to fill the ``ParameterList``.

        Examples
        --------
        >>> neclib.utils.ParameterList.new(3, 100)
        ParameterList([100, 100, 100])

        """
        return cls([initvalue for _ in range(length)])

    def push(self, value: Any) -> None:
        """Append new value to ParameterList, preserving its length.

        Parameters
        ----------
        value
            Value to be appended.

        Examples
        --------
        >>> param = neclib.utils.ParameterList([1, 2])
        >>> param.push(5)
        >>> param
        ParameterList([2, 5])

        """
        self.append(value)
        self.pop(0)

    def copy(self):
        """Return copied ParameterList.

        Examples
        --------
        >>> param = neclib.utils.ParameterList([1, 2])
        >>> param.copy()
        ParameterList([1, 2])

        """
        return self.__class__(super().copy())

    def map(self, func: Callable) -> "ParameterList":
        """Map a function to every element in the ParameterList.

        Parameters
        ----------
        func
            Function to apply.

        Examples
        --------
        >>> param = neclib.utils.ParameterList([1, 2])
        >>> param.map(lambda x: 10 * x)
        ParameterList([10, 20])

        """
        return self.__class__(list(map(func, self)))

    def __repr__(self) -> str:
        return self.__class__.__name__ + "(" + super().__repr__() + ")"


@dataclass
class AzElData:
    az: Any = None
    """Parameter related to azimuth axis."""
    el: Any = None
    """Parameter related to elevation axis."""


class ParameterMapping(dict):
    """Dict, with attribute access to parameter supported.

    Parameter mapping, supports both dict-key syntax and attribute access syntax. Dict
    methods are fully supported.

    Examples
    --------
    >>> param = neclib.utils.ParameterMapping(a=1, b=2)
    >>> param["a"]
    1
    >>> param.a
    1
    >>> neclib.utils.ParameterMapping({"a": 1, "b": 2}) == param
    True

    """

    def __repr__(self) -> str:
        return self.__class__.__name__ + "(" + super().__repr__() + ")"

    def __getattr__(self, name: Hashable) -> Any:
        try:
            return self[name]
        except KeyError as e:  # Raise AttributeError instead of KeyError.
            raise AttributeError(f"No attribute '{name}'") from e

    def copy(self):
        """Return copied ParameterMapping.

        Examples
        --------
        >>> param = neclib.utils.ParameterMapping(a=1, b=2)
        >>> param.copy()
        ParameterMapping({'a': 1, 'b': 2})

        """
        return self.__class__(super().copy())


T = TypeVar("T", bound=SupportsComparison)


class ValueRange(Generic[T]):
    """Utility type for value range checking.

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
    >>> valid_value = neclib.utils.ValueRange(0, 1)
    >>> 0.5 in valid_value
    True
    >>> -1 in valid_value
    False

    >>> valid_str = neclib.utils.ValueRange("aaa", "bbb")
    >>> "abc" in valid_str
    True

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

    def __contains__(self, value: Any) -> bool:
        if self.strict:
            return self.lower < value < self.upper
        return self.lower <= value <= self.upper

    def __iter__(self) -> Iterator[T]:
        return iter((self.lower, self.upper))

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return f"{class_name}({self.lower}, {self.upper}, strict={self.strict})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            return False
        eq_limits = (self.lower == other.lower) and (self.upper == other.upper)
        return eq_limits and self.strict is other.strict

    @property
    def width(self) -> Optional[T]:
        """Width of the range.

        Examples
        --------
        >>> valid_value = neclib.utils.ValueRange(0, 1)
        >>> valid_value.width
        1

        """
        try:
            return self.upper - self.lower
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
        >>> valid_value = neclib.utils.ValueRange(0, 1)
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
        >>> valid_value = neclib.utils.ValueRange(0, 1)
        >>> valid_value.contain_any([0.5, 1.6])
        True

        """
        values = np.asanyarray(values)
        if self.strict:
            ret = ((self.lower < values) & (values < self.upper)).any()
        else:
            ret = ((self.lower <= values) & (values <= self.upper)).any()
        return bool(ret)

    def map(self, func: Callable[[T], Any]) -> "ValueRange":
        """Map a function to upper and lower bounds.

        Parameters
        ----------
        func
            Function to apply.

        Examples
        --------
        >>> valid_value = neclib.utils.ValueRange(0, 1)
        >>> valid_value.map(lambda x: 10 * x)
        ValueRange(0, 10, strict=False)

        """
        return self.__class__(func(self.lower), func(self.upper), self.strict)


def toCamelCase(
    data: str,
    kind: Literal["upper", "pascal", "bumpy", "python", "lower", ""] = "python",
) -> str:
    PascalCase = re.sub(
        r"([A-Za-z])([a-z0-9]*?)(_|$|\s)",
        lambda mo: mo.group(1).upper() + mo.group(2),
        data,
    )
    if kind.lower() in ["upper", "pascal", "bumpy", "python"]:
        return PascalCase
    elif kind.lower() in ["lower", ""]:
        return re.sub(
            r"^([A-Z])([a-z0-9]+?)",
            lambda mo: mo.group(1).lower() + mo.group(2),
            PascalCase,
        )
