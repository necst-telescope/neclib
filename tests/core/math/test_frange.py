import astropy.units as u
import numpy as np
import pytest

from neclib.core.math import frange


class TestFrange:
    def test_int_range(self) -> None:
        assert (frange(1, 10, 2) == [1, 3, 5, 7, 9]).all()

    def test_int_range_inclusive(self) -> None:
        assert (frange(1, 10, 2, inclusive=True) == [1, 3, 5, 7, 9, 10]).all()

    def test_float_range(self) -> None:
        # Element-wise comparison between np.ndarray and list of float values is not
        # supported.
        expected = pytest.approx(np.array([1.0, 3.1, 5.2, 7.3, 9.4]))
        assert frange(1.0, 10.2, 2.1) == expected

    def test_float_range_inclusive(self) -> None:
        expected = pytest.approx(np.array([1.0, 3.1, 5.2, 7.3, 9.4, 10.2]))
        assert frange(1.0, 10.2, 2.1, inclusive=True) == expected

    def test_quantity_range(self) -> None:
        assert (frange(1 * u.m, 10 * u.m, 2 * u.m) == [1, 3, 5, 7, 9] * u.m).all()

    def test_quantity_range_inclusive(self) -> None:
        assert (
            frange(1 * u.m, 10 * u.m, 2 * u.m, inclusive=True)
            == [1, 3, 5, 7, 9, 10] * u.m
        ).all()

    def test_dimensionless_array_range(self) -> None:
        assert (frange([1, 2], [2, 2.1], [3, 1]) == [[1], [2]]).all()
        assert (frange([[1], [2]], [[2], [2.1]], [[3], [1]]) == [[[1]], [[2]]]).all()

    def test_dimensionless_array_range_inclusive(self) -> None:
        assert (
            frange([1, 2], [2, 2.1], [3, 1], inclusive=True) == [[1, 2], [2, 2.1]]
        ).all()
        assert (
            frange([[1], [2]], [[2], [2.1]], [[3], [1]], inclusive=True)
            == [[[1, 2]], [[2, 2.1]]]
        ).all()

    def test_quantity_array_range(self) -> None:
        assert (
            frange([1, 2] * u.m, [2, 2.1] * u.m, [3, 1] * u.m) == [[1], [2]] * u.m
        ).all()
        assert (
            frange([[1], [2]] * u.m, [[2], [2.1]] * u.m, [[3], [1]] * u.m)
            == [[[1]], [[2]]] * u.m
        ).all()

    def test_quantity_array_range_inclusive(self) -> None:
        assert (
            frange([1, 2] * u.m, [2, 2.1] * u.m, [3, 1] * u.m, inclusive=True)
            == [[1, 2], [2, 2.1]] * u.m
        ).all()
        assert (
            frange(
                [[1], [2]] * u.m, [[2], [2.1]] * u.m, [[3], [1]] * u.m, inclusive=True
            )
            == [[[1, 2]], [[2, 2.1]]] * u.m
        ).all()
