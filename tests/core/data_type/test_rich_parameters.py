from pathlib import Path

import astropy.units as u
import pytest

from neclib import NECSTParameterNameError
from neclib.core import RichParameters


class TestRichParameters:
    def test_builtin_value(self) -> None:
        p = RichParameters(**{"x": 1})
        assert p["x"] == 1

        p = RichParameters(**{"x": 1.0, "y_1": "abc"})
        assert p["x"] == 1.0
        assert p["y_1"] == "abc"

        p = RichParameters(x=True, y_1=False)
        assert p["x"] is True
        assert p["y_1"] is False

    def test_quantity_value(self) -> None:
        p = RichParameters(**{"x": 1 * u.m})
        assert p["x"] == 1 * u.m

        p = RichParameters(**{"x": 1 * u.m, "y[km]": 2})
        assert p["x"] == 1 * u.m
        assert p["y"] == 2 * u.km

        p = RichParameters(**{"x[deg]": 1, "y[rad/s]": 2, "z": 3})
        assert p["x"] == 1 * u.deg
        assert p["y"] == 2 * u.rad / u.s
        assert p["z"] == 3

    def test_disallow_reserved_name(self) -> None:
        with pytest.raises(NECSTParameterNameError):
            RichParameters(**{"__slots__": 1})

        with pytest.raises(NECSTParameterNameError):
            RichParameters(**{"attach_parsers": 1, "a": 2})

        with pytest.raises(NECSTParameterNameError):
            RichParameters(**{"param": 1, "attach_parsers[deg]": 2})

    def test_read_file(self, data_dir: Path) -> None:
        from_path = RichParameters.from_file(data_dir / "sample_radio_pointing.toml")
        from_str = RichParameters.from_file(
            str(data_dir / "sample_radio_pointing.toml")
        )
        assert from_path.parameters == from_str.parameters

        with (data_dir / "sample_radio_pointing.toml").open("r") as f:
            from_io = RichParameters.from_file(f)
            assert from_io.parameters == from_path.parameters

    def test_alias(self) -> None:
        p = RichParameters(**{"x": 1}, y=2)
        p.attach_aliases(a="x")
        assert p["x"] == 1
        assert p["a"] == p["x"]

        p = RichParameters(x=1, **{"y[deg]": 2})
        p.attach_aliases(a="x", b="y")
        assert p["x"] == 1
        assert p["y"] == 2 * u.deg
        assert p["a"] == p["x"]
        assert p["b"] == p["y"]

    def test_alias_dont_overwrite_parameter(self) -> None:
        p = RichParameters(x=1, y=2)
        with pytest.raises(NECSTParameterNameError):
            p.attach_aliases(x="y")

        p = RichParameters(x=1, **{"y[m/s]": 2})
        with pytest.raises(NECSTParameterNameError):
            p.attach_aliases(x="y")

    def test_disallow_alias_of_reserved_name(self) -> None:
        p = RichParameters(x=1)
        with pytest.raises(NECSTParameterNameError):
            p.attach_aliases(__slots__="x")

        p = RichParameters(x=1, y=5)
        with pytest.raises(NECSTParameterNameError):
            p.attach_aliases(b="x", _parameters="x")

    def test_disallow_alias_to_unknown_key(self) -> None:
        p = RichParameters(x=1)
        with pytest.raises(NECSTParameterNameError):
            p.attach_aliases(a="y")

        p = RichParameters(x=1, y=5)
        with pytest.raises(NECSTParameterNameError):
            p.attach_aliases(b="z")

    def test_attribute_like_access(self) -> None:
        p = RichParameters(x=1, **{"y[deg]": 2})
        assert p.x == p["x"]
        assert p.y == p["y"]

        p = RichParameters(x_1=1, **{"y[deg]": 2})
        assert p.x_1 == p["x_1"]
        assert p.y == p["y"]

    def test_comparison(self) -> None:
        p1 = RichParameters(a=1, **{"b[deg]": 2})
        p2 = RichParameters(a=1, **{"b[deg]": 2})
        p3 = RichParameters(a=1, **{"b[deg]": 3})
        p4 = RichParameters(a=1, **{"b[deg]": 2, "c": 3})

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

    def test_filtering_getitem(self) -> None:
        p = RichParameters(x_a1=1, x_a2=2, x_a3=3)
        filtered = p["x"]
        assert filtered["a1"] == 1
        assert filtered["a2"] == 2
        assert filtered["a3"] == 3

        p = RichParameters(x_a1_b1=1, x_a2_b1=2, **{"x_a3_b1[deg]": 3})
        filtered = p["x"]
        assert filtered["a1_b1"] == 1
        assert filtered["a2_b1"] == 2
        assert filtered["a3_b1"] == 3 * u.deg

    def test_filtering_getattr(self) -> None:
        p = RichParameters(x_a1=1, x_a2=2, x_a3=3)
        filtered = p.x
        assert filtered.a1 == 1
        assert filtered.a2 == 2
        assert filtered.a3 == 3

        p = RichParameters(x_a1_b1=1, x_a2_b1=2, **{"x_a3_b1[deg]": 3})
        filtered = p.x
        assert filtered.a1_b1 == 1
        assert filtered.a2_b1 == 2
        assert filtered.a3_b1 == 3 * u.deg

    def test_multi_step_filtering(self) -> None:
        p = RichParameters(x_a1_b1=1, x_a2_b1=2, **{"x_a3_b1[deg]": 3})
        filtered = p.x.a1
        assert filtered.b1 == 1
        filtered = p.x.a2
        assert filtered.b1 == 2
        filtered = p.x.a3
        assert filtered.b1 == 3 * u.deg

        p = RichParameters(x_a_b_c1=1, **{"x_a_b_c2[deg]": 2})
        filtered = p.x.a.b
        assert filtered.c1 == 1
        assert filtered.c2 == 2 * u.deg

    def test_empty_filter_result_is_error(self) -> None:
        p = RichParameters(x_a1_b1=1, x_a2_b1=2, **{"x_a3_b1[deg]": 3})
        with pytest.raises(AttributeError):
            p.x.a4
        with pytest.raises(KeyError):
            p["x"]["a4"]

    def test_filtering_preserves_aliases(self) -> None:
        p = RichParameters(x_a1=1, x_a2=2, x_a3=3)
        p.attach_aliases(x_a4="x_a3")
        filtered = p.x
        assert filtered.a4 == filtered.a3

        p = RichParameters(x_a1_b1=1, x_a2_b1=2, **{"x_a3_b1[deg]": 3})
        p.attach_aliases(x_a4_b1="x_a3_b1")
        filtered = p.x
        assert filtered.a4_b1 == filtered.a3_b1

    def test_parameter_parsing(self) -> None:
        p = RichParameters(x=1, **{"y[deg]": 2})
        assert p["x"] == 1
        assert p["y"] == 2 * u.deg
        p.attach_parsers(x=lambda x: x + 1)
        assert p["x"] == 2
        assert p["y"] == 2 * u.deg
        p.attach_parsers(x=lambda x: x + 1, y=lambda y: y + 1 * u.deg)
        assert p["x"] == 2
        assert p["y"] == 3 * u.deg

    def test_filtering_preserves_parsers(self) -> None:
        p = RichParameters(x_a1=1, x_a2=2, x_a3=3)
        p.attach_parsers(x_a1=lambda x: x + 1)
        filtered = p.x
        assert filtered.a1 == 2

        p = RichParameters(x_a1_b1=1, x_a2_b1=2, **{"x_a3_b1[deg]": 3})
        p.attach_parsers(x_a1_b1=lambda x: x + 1)
        filtered = p.x
        assert filtered.a1.b1 == 2

    def test_reusing_parsed_value(self) -> None:
        p = RichParameters(x_a1_b1=1, x_a2_b1=2, **{"x_a3_b1[deg]": 3})
        id1 = id(p.x.a1.b1)

        p.attach_parsers(x_a1_b1=lambda x: u.Quantity(x, unit="m/s"))
        id2 = id(p.x.a1.b1)
        assert id1 != id2
        assert id(p.x.a1.b1) == id2

        p.attach_aliases(x_a4_b1="x_a1_b1")
        assert p.x.a1.b1 == 1 * u.m / u.s
        assert p.x.a4.b1 == 1 * u.m / u.s
        assert id(p.x.a1.b1) == id2
        assert id(p.x.a4.b1) == id2
