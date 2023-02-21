from typing import Generator, Optional, Sequence, Tuple, Union, overload

import numpy as np

from . import Functions, clip


class Random:
    def __init__(self, seed: Optional[int] = None, limits: Optional[Sequence] = None):
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.limits = limits

    def _walk(
        self,
        x: Union[Sequence, float, int, np.ndarray, None],
        mu: Union[int, float],
        noise: Union[int, float],
        stability: Union[int, float],
    ) -> Union[np.ndarray, float]:
        x = np.asanyarray(x) if x is not None else mu
        fluctuation = self.rng.uniform(-noise / 2, noise / 2)
        stability = Functions.Sigmoid(0, 1)(stability)
        f2 = self.rng.uniform(0, stability)
        drift = self.rng.normal(f2 * (mu - x), noise)
        drift_applied = mu if x is None else x + drift

        if self.limits is None:
            return drift_applied + fluctuation
        return clip(drift_applied + fluctuation, *self.limits)  # type: ignore

    @overload
    def walk(
        self,
        mu: Union[int, float],
        noise: Union[int, float],
        stability: Union[int, float],
        *,
        initial: Union[int, float, None] = None,
    ) -> Generator[float, None, None]:
        ...

    @overload
    def walk(
        self,
        mu: Union[int, float],
        noise: Union[int, float],
        stability: Union[int, float],
        *,
        initial: Union[Sequence, np.ndarray],
    ) -> Generator[np.ndarray, None, None]:
        ...

    def walk(
        self,
        mu: Union[int, float],
        noise: Union[int, float],
        stability: Union[int, float],
        *,
        initial: Union[Sequence, float, int, np.ndarray, None] = None,
    ) -> Generator[Union[np.ndarray, float], None, None]:
        x = initial
        while True:
            x = self._walk(x, mu, noise, stability)
            yield x

    @overload
    def fluctuation(
        self,
        noise: Union[int, float],
        *,
        shape: None = None,
    ) -> Generator[float, None, None]:
        ...

    @overload
    def fluctuation(
        self,
        noise: Union[int, float],
        *,
        shape: Tuple[int, ...],
    ) -> Generator[np.ndarray, None, None]:
        ...

    def fluctuation(
        self,
        noise: Union[int, float],
        *,
        shape: Optional[Tuple[int, ...]] = None,
    ) -> Generator[Union[np.ndarray, float], None, None]:
        shape = shape if shape is not None else ()
        while True:
            yield self.rng.uniform(-noise / 2, noise / 2, shape)
