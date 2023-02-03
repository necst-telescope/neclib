import pytest

from neclib.core import ValueRange


class TestValueRange:
    def test_valid_range(self):
        ValueRange(0, 1)
        ValueRange(0.5, 1, True)
        ValueRange(-1, 0, False)
        ValueRange(0, 0)

        with pytest.raises(ValueError):
            ValueRange(-1.5, -2)
            ValueRange(100, -100, True)

    def test_contains(self):
        assert 0 in ValueRange(0, 1)
        assert 0 in ValueRange(-1, 1)
        assert 0 in ValueRange(0, 0)

    def test_contains_strict(self):
        assert 0 not in ValueRange(0, 1, True)
        assert 0 in ValueRange(-1, 1, True)
        assert 0 not in ValueRange(0, 0, True)

    def test_iter(self):
        assert list(ValueRange(0, 1)) == [0, 1]
        assert list(ValueRange(0, 1, True)) == [0, 1]
        assert list(ValueRange(0, 0)) == [0, 0]

    def test_width(self):
        assert ValueRange(0, 1).width == 1
        assert ValueRange(0, 1, True).width == 1
        assert ValueRange(0, 0).width == 0

    def test_types(self):
        assert 0.5 in ValueRange(0, 1)
        assert 100 in ValueRange(0, float("inf"))
        assert "abc" in ValueRange("a", "ac")
        assert b"abc" not in ValueRange(b"a", b"ab")

        assert ValueRange(0, float("inf")).width == float("inf")
        assert ValueRange("a", "b").width is None

    def test_function_mapping(self):
        with pytest.raises(TypeError):
            0.5 in ValueRange("0", "1")
        assert 0.5 in ValueRange("0", "1").map(lambda x: int(x))
        assert ValueRange("0", "1").map(lambda x: int(x)).width == 1
        assert ValueRange("0", "1").map(lambda x: int(x)).upper == 1
