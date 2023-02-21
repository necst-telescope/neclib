import numpy as np

from neclib.core.math import Random


class TestRandom:
    def test_walk(self) -> None:
        generator = Random().walk(0, 1, 0.1)
        for _ in range(10000):
            next(generator)
        assert np.isfinite(next(generator))

    def test_walk_array(self) -> None:
        generator = Random().walk(0, 1, 0.1, initial=[0.3, 0.4])
        for _ in range(10000):
            next(generator)
        assert np.isfinite(next(generator)).all()
        assert len(next(generator)) == 2

    def test_fluctuation(self) -> None:
        generator = Random(seed=1).fluctuation(0.5)
        values = [next(generator) for _ in range(10000)]
        assert np.mean(values) < 0.1

    def test_fluctuation_array(self) -> None:
        generator = Random(seed=1).fluctuation(0.5, shape=(2,))
        values = [next(generator) for _ in range(10000)]
        assert np.mean(values) < 0.1
        assert len(next(generator)) == 2
