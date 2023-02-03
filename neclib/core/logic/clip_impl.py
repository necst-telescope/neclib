__all__ = ["clip"]

from typing import Optional, TypeVar, overload

from ..type_aliases import SupportsComparison

T = TypeVar("T", bound=SupportsComparison)


@overload
def clip(value: T, minimum: T, maximum: T) -> T:
    ...


@overload
def clip(value: T, *, absmax: T) -> T:
    ...


def clip(
    value: T,
    minimum: Optional[T] = None,
    maximum: Optional[T] = None,
    *,
    absmax: Optional[T] = None,
) -> T:
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
        maximum = abs(absmax)  # type: ignore
        minimum = -1 * maximum  # type: ignore
    if minimum > maximum:  # type: ignore
        raise ValueError("Minimum should be less than maximum.")
    return min(max(minimum, value), maximum)  # type: ignore
