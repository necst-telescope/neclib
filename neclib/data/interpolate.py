import math
from copy import deepcopy
from typing import Generic, List, Optional, Sequence, Tuple, TypeVar, Union

import numpy as np

T = TypeVar("T")
Index = TypeVar("Index", int, float)


class Interpolator(Generic[T]):
    """Interpolate Python objects.

    Example
    -------
    >>> interp = neclib.data.interpolate.Interpolator(align_by="x", attrs=["x", "y"])
    >>> x = SimpleNamespace(x=1, y=2)
    >>> xs = [SimpleNamespace(x=0, y=0), SimpleNamespace(x=2, y=100)]
    >>> interp(x, xs)
    SimpleNamespace(x=1.0, y=50.0)

    """

    def __init__(
        self, align_by: Optional[str] = None, attrs: Optional[Sequence[str]] = None
    ) -> None:
        self.align_by = align_by
        self.attrs = attrs

    def _get_sorted(self, x: T, xs: Sequence[T]) -> Tuple[Index, List[Index], List[T]]:
        if self.align_by is None:
            xs = sorted(xs)
            return x, xs, xs
        xs = sorted(xs, key=lambda _x: getattr(_x, self.align_by))
        return getattr(x, self.align_by), [getattr(_x, self.align_by) for _x in xs], xs

    def _get_value(self, lower: T, upper: T, ratio: Union[int, float]) -> T:
        if self.attrs is not None:
            for attr in self.attrs:
                try:
                    lower_attr, upper_attr = getattr(lower, attr), getattr(upper, attr)
                    interp_value = lower_attr + (upper_attr - lower_attr) * ratio
                    setattr(lower, attr, interp_value)
                except Exception:
                    pass
            return lower
        else:
            return lower + (upper - lower) * ratio

    def __call__(self, x: T, xs: Sequence[T]) -> T:
        raise NotImplementedError


class LinearInterp(Interpolator[T]):
    """Interpolate Python objects.

    Example
    -------
    >>> interp = neclib.data.interpolate.LinearInterp(align_by="x", attrs=["x", "y"])
    >>> x = SimpleNamespace(x=1, y=2)
    >>> xs = [SimpleNamespace(x=0, y=0), SimpleNamespace(x=2, y=100)]
    >>> interp(x, xs)
    SimpleNamespace(x=1.0, y=50.0)

    """

    def __call__(self, x: T, xs: Sequence[T]) -> T:
        _x, _xs, xs = self._get_sorted(x, xs)
        idx = np.interp(_x, _xs, range(len(_xs)))
        return self._get_value(
            deepcopy(xs[math.floor(idx)]), deepcopy(xs[math.ceil(idx)]), idx % 1
        )
