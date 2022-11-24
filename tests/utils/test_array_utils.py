import astropy.units as u

from neclib.utils import linear_sequence


class TestLinearSequence:
    def test_scalar(self):
        assert linear_sequence(1, 1, 3).tolist() == [1, 2, 3]
        assert linear_sequence(1, 2, 3).tolist() == [1, 3, 5]
        assert linear_sequence(1, 3.1, 3).tolist() == [1, 4.1, 7.2]
        assert linear_sequence(1.2, 3.1, 3).tolist() == [1.2, 4.3, 7.4]
        assert (linear_sequence(1.2, -2.9, 4) - [1.2, -1.7, -4.6, -7.5] < 1e-6).all()

    def test_vector(self):
        assert linear_sequence([1, 2], [1, 2], 3).tolist() == [[1, 2], [2, 4], [3, 6]]

        expected = [[1.1, 2], [2.3, 6], [3.5, 10]]
        assert (linear_sequence([1.1, 2], [1.2, 4], 3) - expected < 1e-6).all()

    def test_matrix(self):
        start = [[1, 2], [3, 4]]
        step = [[1, 2], [1, 2]]
        expected = [[[1, 2], [3, 4]], [[2, 4], [4, 6]]]
        assert linear_sequence(start, step, 2).tolist() == expected

        start = [[1, 2.1], [3.1, 4]]
        step = [[1, 2.1], [1, 2.2]]
        expected = [[[1, 2.1], [3.1, 4]], [[2, 4.2], [4.1, 6.2]]]
        assert (linear_sequence(start, step, 2) - expected < 1e-6).all()

    def test_quantity(self):
        assert (linear_sequence(1 * u.m, 1 * u.m, 3) == [1, 2, 3] * u.m).all()

        expected = [1, 4.1, 7.2] * u.m
        assert (linear_sequence(1 * u.m, 3.1 * u.m, 3) == expected).all()

        expected = [1.2, 4.3, 7.4] * u.m
        assert (linear_sequence(1.2 * u.m, 3.1 * u.m, 3) == expected).all()

        expected = [1.2, -1.7, -4.6, -7.5] * u.m
        assert (
            linear_sequence(1.2 * u.m, -2.9 * u.m, 4) - expected < (1e-6 * u.m)
        ).all()

    def test_quantity_vector(self):
        expected = [[1, 2], [2, 4], [3, 6]] * u.m
        assert (linear_sequence([1, 2] * u.m, [1, 2] * u.m, 3) == expected).all()

        expected = [[1.1, 2], [2.3, 6], [3.5, 10]] * u.m
        assert (
            linear_sequence([1.1, 2] * u.m, [1.2, 4] * u.m, 3) - expected < (1e-6 * u.m)
        ).all()

    def test_quantity_matrix(self):
        start = [[1, 2], [3, 4]] * u.m
        step = [[1, 2], [1, 2]] * u.m
        expected = [[[1, 2], [3, 4]], [[2, 4], [4, 6]]] * u.m
        assert (linear_sequence(start, step, 2) == expected).all()

        start = [[1, 2.1], [3.1, 4]] * u.m
        step = [[1, 2.1], [1, 2.2]] * u.m
        expected = [[[1, 2.1], [3.1, 4]], [[2, 4.2], [4.1, 6.2]]] * u.m
        assert (linear_sequence(start, step, 2) - expected < (1e-6 * u.m)).all()
