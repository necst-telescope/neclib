import sys

import numpy as np
import pytest

from neclib.utils import (
    AliasedDict,
    AzElData,
    ParameterList,
    ParameterMapping,
    to_snake_case,
    toCamelCase,
)


class TestParameterList:
    def test_init(self):
        assert ParameterList() == ParameterList([])
        assert ParameterList(range(5)) == ParameterList([0, 1, 2, 3, 4])
        assert ParameterList([1, 2])[1] == 2

    def test_new(self):
        assert len(ParameterList.new(5)) == 5
        assert ParameterList.new(2, 0) == ParameterList([0, 0])

    def test_default_to_nan(self):
        assert np.isnan(ParameterList.new(1))

    def test_push(self):
        list_ = ParameterList.new(3, 0)
        list_.push(1)
        assert list_ == ParameterList([0, 0, 1])
        list_.push(2)
        assert list_ == ParameterList([0, 1, 2])

    def test_copy(self):
        original = ParameterList([1, 2])
        copied = original.copy()
        assert isinstance(copied, ParameterList)
        assert original is not copied
        copied.push(3)
        assert copied[1] == 3
        assert original[1] != 3

    def test_map(self):
        original = ParameterList([1, 2])
        assert original.map(lambda x: x + 1) == ParameterList([2, 3])
        assert original.map(lambda x: 2 * x) == ParameterList([2, 4])

    def test_equality(self):
        assert ParameterList([1, 2]) == ParameterList([1, 2])
        assert ParameterList([1, 2]) != ParameterList([2, 1])
        list_ = [0, 1, 2]
        assert ParameterList(list_) == list_
        assert list_ == ParameterList(list_)


class TestAzElData:
    def test_fields(self):
        assert list(AzElData().__dict__.keys()) == ["az", "el"]

    def test_value_assignment(self):
        data = AzElData(az=[1, 2, 3], el=[4, 5, 6])
        data.az[2] = 300
        assert data.az == [1, 2, 300]


PYTHON_VERSION = sys.version_info


class TestParameterMapping:
    def test_args(self):
        param = ParameterMapping(a=1, b=2)
        assert param == ParameterMapping({"a": 1, "b": 2})
        assert param == ParameterMapping(zip(["a", "b"], [1, 2]))
        assert param == ParameterMapping([("a", 1), ("b", 2)])
        assert param == ParameterMapping({"a": 1}, b=2)

    def test_repr(self):
        data = ParameterMapping(a=1, b=2)
        assert repr(data) == "ParameterMapping({'a': 1, 'b': 2})"

    def test_getattr(self):
        test_cases = [
            {"a": 1},
            {"a": 1, "b": 2},
            {"a": "1", "b": 2},
        ]
        for kwargs in test_cases:
            data = ParameterMapping(**kwargs)
            for k, v in kwargs.items():
                assert getattr(data, k) == v

    def test_len(self):
        test_cases = [
            {},
            {"a": 1},
            {"a": 1, "b": 2},
            {"a": "1", "b": 2},
        ]
        for kwargs in test_cases:
            assert len(ParameterMapping(**kwargs)) == len(kwargs)

    def test_getitem(self):
        test_cases = [
            {"a": 1},
            {"a": 1, "b": 2},
            {"a": "1", "b": 2},
        ]
        for kwargs in test_cases:
            data = ParameterMapping(**kwargs)
            for k, v in kwargs.items():
                assert data[k] == v

    def test_setitem(self):
        data = ParameterMapping()
        data["a"] = 1
        assert data["a"] == 1
        data["b"] = 2
        assert data["b"] == 2
        data["a"] = "1"
        assert data["a"] == "1"

    def test_delitem(self):
        data = ParameterMapping(a=1, b=2)
        del data["a"]
        with pytest.raises(KeyError):
            assert data["a"] == 1
        assert data["b"] == 2

    def test_contains(self):
        data = ParameterMapping(a=1, b=2)
        assert "a" in data
        assert "b" in data
        assert "c" not in data

    def test_iter(self):
        data = ParameterMapping(a=1, b=2)

        assert list(iter(data)) == ["a", "b"]

        keys = [k for k in data]
        assert keys == ["a", "b"]

    def test_clear(self):
        data = ParameterMapping(a=1, b=2)
        data.clear()
        assert list(data.keys()) == []

    def test_copy(self):
        data = ParameterMapping(a=1, b=2)
        copied = data.copy()
        assert isinstance(copied, ParameterMapping)
        assert data is not copied
        copied["a"] = 100
        assert copied["a"] == 100
        assert data["a"] != 100

    def test_get(self):
        example = ParameterMapping(a=1, b=2)
        assert example.get("a") == 1
        assert example.get("b", 1) == 2
        assert example.get("c") is None
        assert example.get("c", 100) == 100

    def test_items(self):
        test_cases = [
            {"a": 1},
            {"a": 1, "b": 2},
            {"a": "1", "b": 2},
        ]
        for kwargs in test_cases:
            assert ParameterMapping(**kwargs).items() == kwargs.items()

    def test_keys(self):
        test_cases = [
            {"a": 1},
            {"a": 1, "b": 2},
            {"a": "1", "b": 2},
        ]
        for kwargs in test_cases:
            assert ParameterMapping(**kwargs).keys() == kwargs.keys()

    def test_pop(self):
        example = ParameterMapping(a=1, b=2)
        assert example.pop("a") == 1
        assert ["b"] == list(example.keys())
        with pytest.raises(KeyError):
            _ = example.pop("a")
        assert example.pop("a", 100) == 100

    def test_popitem(self):
        data = ParameterMapping(a=1, b=2)
        assert data.popitem() == ("b", 2)
        assert data.popitem() == ("a", 1)

    @pytest.mark.skipif(
        PYTHON_VERSION < (3, 8),
        reason="Reversing dict object isn't supported for Python < 3.8",
    )
    def test_reversed(self):
        data = ParameterMapping(a=1, b=2)
        assert list(reversed(data)) == ["b", "a"]

    def test_update(self):
        data = ParameterMapping(a=1, b=2)
        additional = ParameterMapping(b=5, c=10)
        data.update(additional)
        assert data == ParameterMapping(a=1, b=5, c=10)

    def test_values(self):
        test_cases = [
            {"a": 1},
            {"a": 1, "b": 2},
            {"a": "1", "b": 2},
        ]
        for kwargs in test_cases:
            assert list(ParameterMapping(**kwargs).values()) == list(kwargs.values())

    def test_eq_ne(self):
        assert ParameterMapping() == ParameterMapping()
        assert ParameterMapping() != ParameterMapping(a=1)
        assert ParameterMapping(a=1, b=2) == ParameterMapping(a=1, b=2)
        assert ParameterMapping(a=1, b=2) != ParameterMapping(a="1", b=2)
        assert ParameterMapping(a=1, b=2) != ParameterMapping(a=2, b=2)

    def test_nonexistent_key(self):
        with pytest.raises(KeyError):
            ParameterMapping()["a"]


class TestToCamelCase:
    @pytest.mark.parametrize("kind", ["upper", "pascal", "bumpy", "python"])
    def test_upper_camel_case(self, kind):
        assert toCamelCase("ABC", kind) == "ABC"
        assert toCamelCase("abc_def", kind) == "AbcDef"
        assert toCamelCase("abc def ghi", kind) == "AbcDefGhi"
        assert toCamelCase("AbcDef", kind) == "AbcDef"

    @pytest.mark.parametrize("kind", ["lower", ""])
    def test_lower_camel_case(self, kind):
        assert toCamelCase("ABC", kind) == "ABC"
        assert toCamelCase("abc_def", kind) == "abcDef"
        assert toCamelCase("abc def ghi", kind) == "abcDefGhi"
        assert toCamelCase("abcDef", kind) == "abcDef"


def test_to_snake_case():
    assert to_snake_case("ABC") == "abc"
    assert to_snake_case("abc_def") == "abc_def"
    assert to_snake_case("abc def ghi") == "abc_def_ghi"
    assert to_snake_case("abcDef") == "abc_def"
    assert to_snake_case("AbcDef") == "abc_def"
    assert to_snake_case("ABC123") == "abc123"


class TestAliasedDict:
    def test_init(self):
        d = AliasedDict({"a": 1, "b": 2})
        assert d["a"] == 1
        assert d["b"] == 2

    def test_alias(self):
        d = AliasedDict({"a": 1, "b": 2})
        d.alias(c="a")
        assert d["a"] == 1
        assert d["c"] == 1

    def test_alias_dont_overwrite_existing_key(self):
        d = AliasedDict({"a": 1, "b": 2})
        with pytest.raises(KeyError):
            d.alias(a="b")

    def test_overwrite_alias(self):
        d = AliasedDict({"a": 1, "b": 2})
        d.alias(c="a")
        d["c"] = 3
        assert d["a"] == 1
        assert d["c"] == 3
