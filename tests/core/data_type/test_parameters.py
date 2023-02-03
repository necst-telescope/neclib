from pathlib import Path

import astropy.units as u
import pytest

from neclib import NECSTAccessibilityWarning, NECSTParameterNameError
from neclib.core import Parameters


class TestParameters:
    def test_builtin_value(self) -> None:
        p = Parameters(a="abc")
        assert p["a"] == "abc"

        p = Parameters(a=1)
        assert p["a"] == 1

        p = Parameters(a=1.01)
        assert p["a"] == 1.01

        p = Parameters(**{"a": True})
        assert p["a"] is True

    def test_quantity_value(self) -> None:
        p = Parameters(**{"distance[pc]": 10})
        assert p["distance"] == 10 * u.pc

        p = Parameters(**{"velocity[pc/s]": -1.1})
        assert p["velocity"] == -1.1 * u.pc / u.s

        p = Parameters(**{"area[pc m]": 1.1})
        assert p["area"] == 1.1 * u.pc * u.m

        p = Parameters(**{"area[km m]": 1.5})
        assert p["area"] == 1.5 * u.km * u.m

    def test_angular_value(self) -> None:
        p = Parameters(**{"angle[deg]": 10})
        assert p["angle"] == 10 * u.deg

        p = Parameters(**{"angle[rad]": 10})
        assert p["angle"] == 10 * u.rad

        p = Parameters(**{"angle[arcmin]": 10})
        assert p["angle"] == 10 * u.arcmin

        p = Parameters(**{"angle[arcsec]": 10})
        assert p["angle"] == 10 * u.arcsec

        p = Parameters(**{"angular_area[deg2]": 10})
        assert p["angular_area"] == 10 * u.deg**2

        p = Parameters(**{"ratio[deg / arcsec]": 10})
        assert p["ratio"] == 10 * u.deg / u.arcsec

    def test_angular_but_dimensional_value(self) -> None:
        p = Parameters(**{"angular_speed[deg / s]": 0.2})
        assert p["angular_speed"] == 0.2 * u.deg / u.s

        p = Parameters(**{"angular_acceleration[rad / s2]": 0.25})
        assert p["angular_acceleration"] == 0.25 * u.rad / u.s**2

        p = Parameters(**{"angular_momentum[arcsec2 / s]": 0.45})
        assert p["angular_momentum"] == 0.45 * u.arcsec**2 / u.s

        p = Parameters(**{"angular_momentum[deg rad / s]": 0.75})
        assert p["angular_momentum"] == 0.75 * u.deg * u.rad / u.s

    def test_multiple_values(self) -> None:
        p = Parameters(**{"a": 1, "b": 2, "c": 3})
        assert p["a"] == 1
        assert p["b"] == 2
        assert p["c"] == 3

        p = Parameters(a=4, b=5, c=6)
        assert p["a"] == 4
        assert p["b"] == 5
        assert p["c"] == 6

        p = Parameters(**{"a": 1, "b[deg]": 2, "c": 3, "d": 4})
        assert p["a"] == 1
        assert p["b"] == 2 * u.deg
        assert p["c"] == 3
        assert p["d"] == 4

        p = Parameters(**{"a[deg]": 45, "b[m]": 3, "c[deg/s]": 9, "d": 0})
        assert p["a"] == 45 * u.deg
        assert p["b"] == 3 * u.m
        assert p["c"] == 9 * u.deg / u.s
        assert p["d"] == 0

    def test_unit_conversion_on_init(self) -> None:
        p = Parameters(**{"a[deg]": "45arcsec", "b[m]": 3})
        assert p["a"] == 45 * u.arcsec
        assert p["b"] == 3 * u.m
        assert p["a"].unit == u.deg
        assert p["a"].value == 45 / 3600

    def test_disallow_reserved_name(self) -> None:
        with pytest.raises(NECSTParameterNameError):
            Parameters(**{"attach_aliases": 0})
        with pytest.raises(NECSTParameterNameError):
            Parameters(**{"__slots__": 1})
        with pytest.raises(NECSTParameterNameError):
            Parameters(**{"attach_aliases[s]": 0})
        with pytest.raises(NECSTParameterNameError):
            Parameters(**{"a": 1, "__slots__[deg]": 1})

    def test_warn_limited_attribute_access(self) -> None:
        with pytest.warns(NECSTAccessibilityWarning):
            p = Parameters(**{"1": 30})
            assert p["1"] == 30
        with pytest.warns(NECSTAccessibilityWarning):
            p = Parameters(**{"q": 10, "1": 30})
            assert p["q"] == 10
            assert p["1"] == 30

    def test_read_file(self, data_dir: Path) -> None:
        from_path = Parameters.from_file(data_dir / "sample_radio_pointing.toml")
        from_str = Parameters.from_file(str(data_dir / "sample_radio_pointing.toml"))
        assert from_str.parameters == from_path.parameters

        with (data_dir / "sample_radio_pointing.toml").open("r") as f:
            from_io = Parameters.from_file(f)
            assert from_io.parameters == from_path.parameters

    def test_alias(self) -> None:
        p = Parameters(a=1, b=2)
        p.attach_aliases(c="b")
        assert p["b"] == 2
        assert p["c"] == p["b"]

        p = Parameters(**{"a[deg]": 3, "b": 2})
        p.attach_aliases(c="b")
        assert p["a"] == 3 * u.deg
        assert p["b"] == 2
        assert p["c"] == p["b"]

        p = Parameters(**{"a[deg]": 3, "b": 2})
        p.attach_aliases(c="a")
        assert p["a"] == 3 * u.deg
        assert p["b"] == 2
        assert p["c"] == p["a"]

    def test_multiple_aliases(self) -> None:
        p = Parameters(**{"a[deg]": 3, "b": 2})
        p.attach_aliases(c="a", **{"p": "b"})
        assert p["a"] == 3 * u.deg
        assert p["b"] == 2
        assert p["c"] == 3 * u.deg
        assert p["p"] == 2

        p = Parameters(**{"a[deg]": 3, "b": 2})
        p.attach_aliases(c="a", **{"p": "a"})
        assert p["a"] == 3 * u.deg
        assert p["b"] == 2
        assert p["c"] == 3 * u.deg
        assert p["p"] == 3 * u.deg

    def test_alias_dont_overwrite_parameter(self) -> None:
        p = Parameters(**{"a": 3, "b": 2})
        with pytest.raises(NECSTParameterNameError):
            p.attach_aliases(b="a")

        p = Parameters(**{"a": 3, "b": 2})
        with pytest.raises(NECSTParameterNameError):
            p.attach_aliases(c="a", **{"b": "a"})

        p = Parameters(**{"a[deg]": 3, "b": 2})
        with pytest.raises(NECSTParameterNameError):
            p.attach_aliases(b="a", **{"p": "a"})

    def test_disallow_alias_of_reserved_name(self) -> None:
        p = Parameters(**{"a": 3, "b": 2})
        with pytest.raises(NECSTParameterNameError):
            p.attach_aliases(parameters="a")

        p = Parameters(**{"a": 3, "b": 2})
        with pytest.raises(NECSTParameterNameError):
            p.attach_aliases(__slots__="a")

    def test_disallow_alias_to_unknown_key(self) -> None:
        p = Parameters(**{"a": 3, "b": 2})
        with pytest.raises(NECSTParameterNameError):
            p.attach_aliases(c="q")

        p = Parameters(**{"a": 3, "b": 2})
        with pytest.raises(NECSTParameterNameError):
            p.attach_aliases(c="a", **{"p": "q"})

        p = Parameters(**{"a[deg]": 3, "b": 2})
        with pytest.raises(NECSTParameterNameError):
            p.attach_aliases(c="a", **{"p": "q"})

    def test_attribute_like_access(self) -> None:
        p = Parameters(a=1)
        assert p["a"] == p.a

        p = Parameters(**{"a": 1, "b[deg]": 300, "c[m/s]": 10})
        assert p["a"] == p.a
        assert p["b"] == p.b
        assert p["c"] == p.c

    def test_attribute_like_access_to_alias(self) -> None:
        p = Parameters(a=1, b=2)
        p.attach_aliases(c="b")
        assert p.b == 2
        assert p.c == p.b

        p = Parameters(**{"a[deg]": 3, "b": 2})
        p.attach_aliases(c="b")
        assert p.a == 3 * u.deg
        assert p.b == 2
        assert p.c == p.b

    def test_comparison(self) -> None:
        p1 = Parameters(a=1, **{"b[deg]": 2})
        p2 = Parameters(a=1, **{"b[deg]": 2})
        p3 = Parameters(a=1, **{"b[deg]": 3})
        p4 = Parameters(a=1, **{"b[deg]": 2, "c": 3})

        assert p1 == p2
        assert p1 != p3
        assert p1 != p4
        assert p1 <= p2

        assert p1 < p4
        assert p1 <= p4

        assert not p1 <= p3
        assert not p1 < p3
        assert not p1 > p3
        assert not p1 >= p3

        assert not p2 <= p3
        assert not p2 < p3
        assert not p2 > p3
        assert not p2 >= p3

    def test_comparison_with_other_type(self) -> None:
        p = Parameters(a=1, **{"b[deg]": 2})

        assert not p == 1
        assert p != "ab"

        with pytest.raises(TypeError):
            _ = p > [1, 2 * u.deg]
        with pytest.raises(TypeError):
            _ = p < {"a": 1, "b": 2 * u.deg}
        with pytest.raises(TypeError):
            _ = p >= [1, 2]
        with pytest.raises(TypeError):
            _ = p <= {"a": 1, "b": 2 * u.deg}
