from types import SimpleNamespace

import pytest

from neclib.data import LinearExtrapolate


class TestLinearExtrapolate:
    def test_array(self):
        interp = LinearExtrapolate()
        assert interp(100, [0, 2]) == 100

    def test_two_objects(self):
        interp = LinearExtrapolate(align_by="x", attrs=["x", "y"])
        x = SimpleNamespace(x=100)
        xs = [SimpleNamespace(x=0, y=90), SimpleNamespace(x=2, y=100)]
        result = interp(x, xs)
        assert result.x == 100
        assert result.y == pytest.approx(590)

    def test_many_objects(self):
        interp = LinearExtrapolate(align_by="x", attrs=["x", "y"])
        x = SimpleNamespace(x=100)
        xs = [
            SimpleNamespace(x=0, y=90),
            SimpleNamespace(x=2, y=100),
            SimpleNamespace(x=4, y=110),
            SimpleNamespace(x=6, y=120),
        ]
        result = interp(x, xs)
        assert result.x == 100
        assert result.y == pytest.approx(590)

    def test_not_interpolatable_field(self):
        interp = LinearExtrapolate(align_by="x", attrs=["x", "y", "z"])
        x = SimpleNamespace(x=100)
        xs = [
            SimpleNamespace(x=0, y=90, z="a"),
            SimpleNamespace(x=2, y=100, z="b"),
            SimpleNamespace(x=4, y=110, z="c"),
            SimpleNamespace(x=6, y=120, z="d"),
        ]
        result = interp(x, xs)
        assert result.x == 100
        assert result.y == pytest.approx(590)
