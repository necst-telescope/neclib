from types import SimpleNamespace

from neclib.data import LinearInterp


class TestLinearInterp:
    def test_array(self):
        interp = LinearInterp()
        assert interp(1, [0, 2]) == 1

    def test_two_objects(self):
        interp = LinearInterp(align_by="x", attrs=["x", "y"])
        x = SimpleNamespace(x=1)
        xs = [SimpleNamespace(x=0, y=90), SimpleNamespace(x=2, y=100)]
        assert interp(x, xs) == SimpleNamespace(x=1, y=95)

    def test_many_objects(self):
        interp = LinearInterp(align_by="x", attrs=["x", "y"])
        x = SimpleNamespace(x=1)
        xs = [
            SimpleNamespace(x=0, y=90),
            SimpleNamespace(x=2, y=100),
            SimpleNamespace(x=3, y=110),
            SimpleNamespace(x=4, y=120),
        ]
        assert interp(x, xs) == SimpleNamespace(x=1, y=95)

    def test_not_interpolatable_field(self):
        interp = LinearInterp(align_by="x", attrs=["x", "y", "z"])
        x = SimpleNamespace(x=1)
        xs = [
            SimpleNamespace(x=0, y=90, z="a"),
            SimpleNamespace(x=2, y=100, z="b"),
            SimpleNamespace(x=3, y=110, z="c"),
            SimpleNamespace(x=4, y=120, z="d"),
        ]
        result = interp(x, xs)
        assert result.x == 1
        assert result.y == 95
