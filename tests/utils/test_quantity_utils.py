import astropy.units as u
import numpy as np
import pytest
from astropy.units import UnitConversionError

from neclib.utils import (
    angle_conversion_factor,
    parse_quantity,
    partially_convert_unit,
    quantity2builtin,
    dAz2dx,
    dx2dAz,
    get_quantity,
)


def test_angle_conversion_factor():
    test_cases = [
        (["deg", "arcsec"], 3600),
        (["deg", "arcmin"], 60),
        (["deg", "deg"], 1),
        (["arcmin", "arcsec"], 60),
        (["arcmin", "arcmin"], 1),
        (["arcmin", "deg"], 1 / 60),
        (["arcsec", "arcsec"], 1),
        (["arcsec", "arcmin"], 1 / 60),
        (["arcsec", "deg"], 1 / 3600),
    ]
    for args, expected in test_cases:
        assert angle_conversion_factor(*args) == expected


def test_parse_quantity():
    test_cases = [
        # String inputs
        [("1kg",), {}, 1 << u.kg],
        [("1 J",), {}, 1 << u.J],
        [("1 m",), {"unit": "km"}, 1e-3 << u.km],
        [("1 m / s",), {"unit": "km/h"}, 3.6 << u.km / u.h],
        [("1 m s-1",), {"unit": "km"}, 0.001 << u.km / u.s],
        # Quantity inputs
        [(1 << u.s,), {}, 1 << u.s],
        [(1 << u.s,), {"unit": "h"}, 1 / 3600 << u.h],
        [(1 << u.s,), {"unit": u.h}, 1 / 3600 << u.h],
        [("1s",), {"unit": u.h}, 1 / 3600 << u.h],
    ]
    for args, kwargs, expected in test_cases:
        result = parse_quantity(*args, **kwargs)
        assert result == expected
        assert result.value == expected.value


def test_partially_convert_unit():
    test_cases = [
        [(1 << u.km, "m"), 1000 << u.m],
        [(1 << u.km, u.m), 1000 << u.m],
        [(1 << u.Unit("kg m2 s-2"), "kg m s"), 1 << u.J],
        [(1 << u.Unit("kg m2 s-2"), "g cm s"), 1e7 << u.erg],
        [(1 << u.Unit("kg m2 s-2"), "g cm"), 1e7 << u.erg],
        [(1 << u.Unit("kg m2 s-2"), "g2 cm2"), 1e7 << u.erg],
    ]
    for args, expected in test_cases:
        result = partially_convert_unit(*args)
        assert result == expected
        assert result.value == expected.value


def test_quantity2builtin():
    _1kms = 1 << u.km / u.s
    _1hr = 3600 << u.s
    unit_form1_cases = [
        [({"a": _1kms}, {"a": u.Unit("km/s")}), {"a": 1}],
        [
            ({"a": _1kms, "b": _1hr}, {"a": u.Unit("km/s"), "b": "h"}),
            {"a": 1, "b": 1},
        ],
        [
            ({"a": _1kms, "b": True}, {"a": u.Unit("km/s")}),
            {"a": 1, "b": True},
        ],
        [
            ({"a": _1kms, "b": 2 * _1kms}, {"a": u.Unit("km/s"), "b": u.Unit("km/s")}),
            {"a": 1, "b": 2},
        ],
    ]
    for args, expected in unit_form1_cases:
        result = quantity2builtin(*args)
        assert result == expected

    unit_form2_cases = [
        [({"a": _1kms}, {u.Unit("km/s"): ["a"]}), {"a": 1}],
        [
            ({"a": _1kms, "b": _1hr}, {u.Unit("km/s"): ["a"], "h": ["b"]}),
            {"a": 1, "b": 1},
        ],
        [
            ({"a": _1kms, "b": True}, {u.Unit("km/s"): ["a"]}),
            {"a": 1, "b": True},
        ],
        [
            ({"a": _1kms, "b": 2 * _1kms}, {u.Unit("km/s"): ["a", "b"]}),
            {"a": 1, "b": 2},
        ],
    ]
    for args, expected in unit_form2_cases:
        result = quantity2builtin(*args)
        assert result == expected

    unit_form_mixed_cases = [
        [
            ({"a": _1kms, "b": _1hr}, {u.Unit("km/s"): ["a"], "b": "h"}),
            {"a": 1, "b": 1},
        ],
        [
            ({"a": _1kms, "b": 2 * _1kms}, {u.Unit("km/s"): ["a"], "b": "km/s"}),
            {"a": 1, "b": 2},
        ],
    ]
    for args, expected in unit_form_mixed_cases:
        result = quantity2builtin(*args)
        assert result == expected


def test_dAz2dx():
    test_cases = [
        ([30, 216000, "arcsec"], 15),
        ([30, 216000, u.arcsec], 15),
        ([u.Quantity("30arcsec"), u.Quantity("60deg"), "arcsec"], 15),
        ([u.Quantity("30arcsec"), u.Quantity("60deg"), u.arcsec], 15),
        ([u.Quantity("30arcsec"), 60, "deg"], 15 / 3600),
    ]
    for args, expected in test_cases:
        assert dAz2dx(*args) == pytest.approx(expected)


def test_dx2dAz():
    test_cases = [
        ([15, 216000, "arcsec"], 30),
        ([15, 216000, u.arcsec], 30),
        ([u.Quantity("15arcsec"), u.Quantity("60deg"), "arcsec"], 30),
        ([u.Quantity("15arcsec"), u.Quantity("60deg"), u.arcsec], 30),
        ([u.Quantity("15arcsec"), 60, "deg"], 30 / 3600),
    ]
    for args, expected in test_cases:
        assert dx2dAz(*args) == pytest.approx(expected)


class TestGetQuantity:
    def test_no_unit_single_value(self):
        assert get_quantity("5deg") == 5 << u.deg
        assert get_quantity(5) == 5
        assert get_quantity(5.0) == 5.0
        assert get_quantity(5 << u.deg) == 5 << u.deg
        assert get_quantity(5 << u.deg).unit is u.deg
        assert (get_quantity(np.arange(5)) == np.arange(5)).all()

    def test_no_unit_multiple_value(self):
        assert get_quantity("5deg", "7min") == (5 << u.deg, 7 << u.min)
        assert get_quantity(5, "7min") == (5, 7 << u.min)
        assert get_quantity(5.0, 7 << u.min) == (5.0, 7 << u.min)
        assert (get_quantity(np.arange(5), 7)[0] == np.arange(5)).all()

    def test_single_value(self):
        assert get_quantity(5, unit="deg") == 5 << u.deg
        assert get_quantity(5.0, unit="deg") == 5 << u.deg
        assert get_quantity("5", unit="deg") == 5 << u.deg
        assert (get_quantity(np.arange(5), unit="deg") == np.arange(5) * u.deg).all()
        assert get_quantity(5 << u.deg, unit="deg") == 5 << u.deg
        assert get_quantity(3600 << u.arcsec, unit="deg") == 1 << u.deg
        assert get_quantity(3600 << u.arcsec, unit="deg").unit is u.deg

    def test_multiple_value(self):
        with pytest.raises(UnitConversionError):
            get_quantity("5deg", "7min", unit="deg")
        assert get_quantity("5deg", "7deg", unit="deg") == (5 << u.deg, 7 << u.deg)
        assert get_quantity(5, "7deg", unit="deg") == (5 << u.deg, 7 << u.deg)
        assert get_quantity(5.0, u.Quantity("7deg"), unit="deg") == (
            5 << u.deg,
            7 << u.deg,
        )
        assert (
            get_quantity(np.arange(5), 7, unit="deg")[0] == np.arange(5) << u.deg
        ).all()
