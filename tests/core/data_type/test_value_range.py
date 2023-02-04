import pytest

from neclib.core import ValueRange


class TestValueRange:
    def test_valid_range(self) -> None:
        ValueRange(0, 1)
        ValueRange(0.5, 1, True)
        ValueRange(-1, 0, False)
        ValueRange(0, 0)

        with pytest.raises(ValueError):
            ValueRange(-1.5, -2)
            ValueRange(100, -100, True)

    def test_contains(self) -> None:
        assert 0 in ValueRange(0, 1)
        assert 0 in ValueRange(-1, 1)
        assert 0 in ValueRange(0, 0)

    def test_contains_strict(self) -> None:
        assert 0 not in ValueRange(0, 1, True)
        assert 0 in ValueRange(-1, 1, True)
        assert 0 not in ValueRange(0, 0, True)

    def test_iter(self) -> None:
        assert list(ValueRange(0, 1)) == [0, 1]
        assert list(ValueRange(0, 1, True)) == [0, 1]
        assert list(ValueRange(0, 0)) == [0, 0]

    def test_width(self) -> None:
        assert ValueRange(0, 1).width == 1
        assert ValueRange(0, 1, True).width == 1
        assert ValueRange(0, 0).width == 0

    def test_types(self) -> None:
        assert 0.5 in ValueRange(0, 1)
        assert 100 in ValueRange(0, float("inf"))
        assert "abc" in ValueRange("a", "ac")
        assert b"abc" not in ValueRange(b"a", b"ab")

        assert ValueRange(0, float("inf")).width == float("inf")
        assert ValueRange("a", "b").width is None

    def test_contain_all(self) -> None:
        assert ValueRange(0, 1).contain_all([0.5, 1.6]) is False
        assert ValueRange(0, 1).contain_all([0, 0.6]) is True

        assert ValueRange(0, 1, True).contain_all([0.5, 1.6]) is False
        assert ValueRange(0, 1, True).contain_all([0, 0.6]) is False

    def test_contain_any(self) -> None:
        assert ValueRange(0, 1).contain_any([0.5, 1.6]) is True
        assert ValueRange(0, 1).contain_any([1, 1.6]) is True
        assert ValueRange(0, 1).contain_any([1.5, 1.6]) is False

        assert ValueRange(0, 1, True).contain_any([0.5, 1.6]) is True
        assert ValueRange(0, 1, True).contain_any([1, 1.6]) is False
        assert ValueRange(0, 1, True).contain_any([1.5, 1.6]) is False

    def test_function_mapping(self) -> None:
        with pytest.raises(TypeError):
            _ = 0.5 in ValueRange("0", "1")
        assert 0.5 in ValueRange("0", "1").map(lambda x: int(x))
        assert ValueRange("0", "1").map(lambda x: int(x)).width == 1
        assert ValueRange("0", "1").map(lambda x: int(x)).upper == 1

    def test_not_support_comparison_type_is_error(self) -> None:
        class A:
            pass

        with pytest.raises(TypeError):
            _ = ValueRange(A(), A()) == 1
