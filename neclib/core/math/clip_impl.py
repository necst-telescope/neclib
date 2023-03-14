from typing import Optional, TypeVar, overload

from ..types import SupportsComparison

T = TypeVar("T", bound=SupportsComparison)


@overload
def clip(value: T, minimum: T, maximum: T, /) -> T:
    ...


@overload
def clip(value: T, absmax: T, /) -> T:
    ...


def clip(value: T, minimum: Optional[T] = None, maximum: Optional[T] = None, /) -> T:
    """Limit the ``value`` to the range [``minimum``, ``maximum``].

    Parameters
    ----------
    value
        Arbitrary parameter.
    minimum
        Lower limit of ``value``, if ``maximum`` is given. Otherwise, absolute value of
        this is used as the upper limit, and negative of that is the lower limit.
    maximum
        Upper limit of ``value``.

    Examples
    --------
    >>> neclib.utils.clip(1.2, 0, 1)
    1
    >>> neclib.utils.clip(41, 0, 100)
    41
    >>> neclib.utils.clip(-4, 3)
    -3

    """
    if minimum is None:
        raise ValueError("Bounding value required.")
    _max = maximum if maximum is not None else abs(minimum)  # type: ignore
    _min = minimum if maximum is not None else -1 * _max  # type: ignore
    if _min > _max:
        raise ValueError("Minimum should be less than maximum.")
    return min(max(_min, value), _max)  # type: ignore
