import astropy.units as u
import pytest

from neclib.utils import ConditionChecker, counter, discretize, frange


class TestFRange:
    def test_unity_step(self):
        assert list(frange(0, 1)) == [0]
        assert list(frange(0 << u.deg, 1 << u.deg)) == [0 << u.deg]

    def test_unity_step_inclusive(self):
        assert list(frange(0, 1, inclusive=True)) == [0, 1]
        assert list(frange(0 << u.deg, 1 << u.deg, inclusive=True)) == [
            0 << u.deg,
            1 << u.deg,
        ]

    def test_float_step(self):
        assert list(frange(0, 1, 0.5)) == [0, 0.5]
        assert list(frange(0 << u.deg, 1 << u.deg, 0.5 << u.deg)) == [
            0 << u.deg,
            0.5 << u.deg,
        ]

    def test_stop_mismatch(self):
        assert list(frange(0, 0.5, 0.3)) == pytest.approx([0, 0.3])
        result = list(frange(0 << u.deg, 0.5 << u.deg, 0.3 << u.deg))
        assert list(map(lambda x: x.value, result)) == pytest.approx([0, 0.3])

    def test_stop_mismatch_inclusive(self):
        assert list(frange(0, 0.5, 0.3, inclusive=True)) == pytest.approx([0, 0.3])
        result = list(frange(0 << u.deg, 0.5 << u.deg, 0.3 << u.deg, inclusive=True))
        assert list(map(lambda x: x.value, result)) == pytest.approx([0, 0.3])

    def test_unsupport_descending_order(self):
        # This is expected behavior, since ``list(range(1, 0))`` outputs ``[]``.
        assert list(frange(1, 0)) == []
        assert list(frange(1 << u.deg, 0 << u.deg)) == []

    def test_unsupport_descending_order_inclusive(self):
        assert list(frange(1, 0, inclusive=True)) == []
        assert list(frange(1 << u.deg, 0 << u.deg, inclusive=True)) == []


def test_discretize():
    test_cases = [
        ([5], 5),
        ([5, 0, 1], 5),
        ([5, 1, 1], 5),
        ([5, 0, 0.1], 5),
        ([5, 0, 0.3], 5.1),
        ([-5, 0, -0.3], -5.1),
        ([-5], -5),
        ([-5, 0, 1], -5),
        ([-5, 1, 1], -5),
        ([-5, 0, 0.1], -5),
        ([-5, 0, 0.3], -5.1),
        ([-5, 0, -0.3], -5.1),
    ]
    for args, expected in test_cases:
        assert discretize(*args) == expected

    test_cases = [
        ([5, 0, 0.3], {"method": "nearest"}, 5.1),
        ([5, 0, 0.3], {"method": "ceil"}, 5.1),
        ([5, 0, 0.3], {"method": "floor"}, 4.8),
        ([-5, 0, 0.3], {"method": "nearest"}, -5.1),
        ([-5, 0, 0.3], {"method": "ceil"}, -4.8),
        ([-5, 0, 0.3], {"method": "floor"}, -5.1),
    ]
    for args, kwargs, expected in test_cases:
        assert discretize(*args, **kwargs) == expected


def test_counter():
    list_safe_cases = [
        (0, []),
        (1, [0]),
        (5, [0, 1, 2, 3, 4]),
    ]
    for stop, expected in list_safe_cases:
        assert list(counter(stop)) == expected

    # Negative number of counts isn't supported.
    with pytest.raises(ValueError):
        list(counter(-1))

    # Stop is None raises error to prevent unintended infinity counter, which
    # potentially causes memory leak.
    with pytest.raises(ValueError):
        a = counter()
        list(a)  # Error is raised on iteration, not on object creation.

    # When stop is None and allow_infty is True, count up to infinity.
    a = counter(allow_infty=True)
    assert next(a) == 0
    assert next(a) == 1
    for i, x in enumerate(a):
        if x > 1e5:  # Assume this will go infinity.
            break
        if i > 1e5:
            assert False, "Failed to count up to 1e5."


class TestConditionChecker:
    def test_default(self):
        assert ConditionChecker().check(True) is True
        assert ConditionChecker().check(False) is False

    def test_sequential(self):
        checker = ConditionChecker(sequential=3)
        assert checker.check(True) is False
        assert checker.check(True) is False
        assert checker.check(True) is True

    def test_reset_on_failure(self):
        checker = ConditionChecker(sequential=3)
        assert checker.check(True) is False
        assert checker.check(True) is False
        assert checker.check(False) is False
        assert checker.check(True) is False
        assert checker.check(True) is False
        assert checker.check(True) is True

    def test_not_reset_on_failure(self):
        checker = ConditionChecker(sequential=3, reset_on_failure=False)
        assert checker.check(True) is False
        assert checker.check(True) is False
        assert checker.check(False) is False
        assert checker.check(True) is True
