from typing import Any, Callable, List, Optional, TypeVar, Union, overload

import astropy.units as u
import numpy as np
import numpy.typing as npt

from ..types import DimensionLess

T = TypeVar("T", bound=Union[DimensionLess, npt.NDArray[Any], u.Quantity])


@overload
def frange(
    stop: Union[DimensionLess, npt.NDArray[Any], u.Quantity],
    /,
    *,
    inclusive: bool = False,
    pad_method: Union[str, Callable[..., Any]] = "edge",
    **pad_kwargs: Any,
) -> npt.NDArray[Any]:
    ...


@overload
def frange(
    start: T,
    stop: T,
    step: Optional[T] = None,
    /,
    *,
    inclusive: bool = False,
    pad_method: Union[str, Callable[..., Any]] = "edge",
    **pad_kwargs: Any,
) -> npt.NDArray[Any]:
    ...


def frange(
    a: T,
    b: Optional[T] = None,
    c: Optional[T] = None,
    /,
    *,
    inclusive: bool = False,
    pad_method: Union[str, Callable[..., Any]] = "edge",
    **pad_kwargs: Any,
) -> npt.NDArray[Any]:
    """A range function with support for quantities, float values, and arrays.

    Parameters
    ----------
    start
        First value to be generated.
    stop
        Last value to be generated is equal to or less than this value.
    step
        Spacing between values.
    inclusive
        If ``True``, ``stop`` is included in the range, no matter what ``step`` is.
    pad_method
        Method to use for padding the last value to match the length of the other
        values. See
        `numpy.pad <https://numpy.org/doc/stable/reference/generated/numpy.pad.html>`_
        for more details.
    pad_kwargs
        Keyword arguments for
        `numpy.pad <https://numpy.org/doc/stable/reference/generated/numpy.pad.html>`_.

    Returns
    -------
    Array of values.

    Raises
    ------
    TypeError
        If arguments are mixture of quantities or non-quantities.
    UnitConversionError
        If any of the arguments have non-equivalent physical dimension.
    UnitConversionError
        If any of the arguments are given as sequence of quantities.

    Examples
    --------
    >>> frange(1, 10, 2)
    array([1, 3, 5, 7, 9, 10])
    >>> frange(1 * u.m, 10 * u.m, 2 * u.m)
    <Quantity [ 1.,  3.,  5.,  7.,  9., 10.] m>
    >>> frange([1, 2], [2, 2.1], [3, 1])
    array([[1. , 2. ],
           [2. , 2.1]])

    """
    if b is None:
        return frange(np.zeros_like(a), a, np.ones_like(a))
    if c is None:
        return frange(a, b, np.ones_like(a))  # type: ignore

    # Splitting the unit is workaround for the issue:
    # https://docs.astropy.org/en/stable/known_issues.html#numpy-array-creation-functions-cannot-be-used-to-initialize-quantity
    unit: Union[int, u.UnitBase] = 1
    if (
        isinstance(a, u.Quantity)
        and isinstance(b, u.Quantity)
        and isinstance(c, u.Quantity)
    ):
        unit = a.unit  # type: ignore
        a, b, c = a.to_value(unit), b.to_value(unit), c.to_value(unit)  # type: ignore
    if (
        isinstance(a, u.Quantity)
        or isinstance(b, u.Quantity)
        or isinstance(c, u.Quantity)
    ):
        raise TypeError(
            "All arguments must be quantities or non-quantities, not mixture of them."
        )

    start, stop, step = np.asanyarray(a), np.asanyarray(b), np.asanyarray(c)
    start, stop, step = np.broadcast_arrays(start, stop, step)
    zero_dimensional: bool = start.ndim == 0

    sequence: List[npt.NDArray[Any]] = [
        np.arange(_start, _stop, _step)
        for _start, _stop, _step in zip(start.flat, stop.flat, step.flat)
    ]

    # Ensure stop value is covered
    if inclusive:
        sequence = [
            np.pad(s, (0, 1), "constant", constant_values=_stop)
            for s, _stop in zip(sequence, stop.flat)
        ]
    length = max(len(s) for s in sequence)
    sequence = [
        np.pad(s, (0, length - len(s)), pad_method, **pad_kwargs)  # type: ignore
        for s in sequence
    ]
    ret = np.asanyarray(sequence[0] if zero_dimensional else sequence)

    if inclusive:
        stop_is_duplicated = np.bool_(ret[..., -2] == ret[..., -1])
    else:
        stop_is_duplicated = np.bool_(False)

    if isinstance(stop_is_duplicated, np.ndarray):
        if stop_is_duplicated.size == 0:
            stop_is_duplicated = np.bool_(False)
        stop_is_duplicated = stop_is_duplicated.all()

    ret = ret * unit
    if stop_is_duplicated:
        ret = ret[..., :-1]
    return ret if zero_dimensional else np.reshape(ret, (*start.shape, -1))
