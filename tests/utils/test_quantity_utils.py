import astropy.units as u

from neclib.utils import (
    angle_conversion_factor,
    parse_quantity,
    partially_convert_unit,
    quantity2builtin,
    optimum_angle,
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


def test_optimum_angle():
    keys = ["current", "target", "limits", "margin", "unit"]
    args = [
        # If there's no choice but to drive >180deg, do so.
        ([15, 200, [0, 360], 5, "deg"], [200]),
        # If there're multiple choices, select shorter path.
        ([15, 200, [-270, 270], 20, "deg"], [-160]),
        # Even if up to 100 turns are accepted.
        ([18000, 30, [-36000, 36000], 20, "deg"], [18030]),
        # Avoid driving into coords close to limits.
        ([240, 260, [-270, 270], 20, "deg"], [-100]),
        # Except in the case the target is within 5deg from current coord.
        ([265, 266, [-270, 270], 20, "deg"], [266]),
        # If there's two equally acceptable candidates, return either of them.
        ([0, 180, [-270, 270], 20, "deg"], [-180, 180]),
        # Of cause in other units.
        ([900, 12000, [-16200, 16200], 1200, "arcmin"], [-9600]),
        ([54000, 720000, [-972000, 972000], 72000, "arcsec"], [-576000]),
    ]
    test_cases = [({k: v for k, v in zip(keys, arg)}, ans) for arg, ans in args]

    for kwargs, ans in test_cases:
        assert optimum_angle(**kwargs) in ans
