from copy import deepcopy
from typing import Sequence, TypeVar

import numpy as np

from neclib.data.interpolate import Interpolator

T = TypeVar("T")
Index = TypeVar("Index", int, float)


class LinearExtrapolate(Interpolator[T]):
    """Extrapolate Python objects.

    Example
    -------
    >>> ext = neclib.data.interpolate.LinearInterp(align_by="x", attrs=["x", "y"])
    >>> x = SimpleNamespace(x=4)
    >>> xs = [SimpleNamespace(x=0, y=0), SimpleNamespace(x=2, y=100)]
    >>> ext(x, xs)
    SimpleNamespace(x=4.0, y=200.0)

    """

    def _extrapolate(self, idx: float, xs: Sequence[T]) -> T:
        ret_x = deepcopy(xs[0])
        if self.attrs is not None:
            for attr in self.attrs:
                try:
                    _xs = [getattr(_x, attr) for _x in xs]
                    slope, intercept = np.polyfit(range(len(xs)), _xs, 1)
                    v = slope * idx + intercept
                    setattr(ret_x, attr, v)
                except Exception:
                    pass
            return ret_x
        else:
            slope, intercept = np.polyfit(range(len(xs)), xs, 1)
            return slope * idx + intercept

    def __call__(self, x: T, xs: Sequence[T]) -> T:
        _x, _xs, xs = self._get_sorted(x, xs)
        slope, intercept = np.polyfit(range(len(_xs)), _xs, 1)
        idx = (_x - intercept) / slope
        return self._extrapolate(idx, xs)
