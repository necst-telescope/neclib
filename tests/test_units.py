import astropy.units as u

from neclib.units import point, scan, scan_to_point_equivalency


def test_parsable():
    assert u.Unit("point") is point
    assert u.Unit("scan") is scan


def test_equivalency():
    assert (3 << point).to(scan, equivalencies=scan_to_point_equivalency(3)) == (
        1 << scan
    )
    assert (10 << scan).to(point, equivalencies=scan_to_point_equivalency(5)) == (
        50 << point
    )

    # Raise no error if no conversion is done.
    assert (3 << point).to(point, equivalencies=scan_to_point_equivalency(3)) == (
        3 << point
    )
    assert (10 << scan).to(scan, equivalencies=scan_to_point_equivalency(5)) == (
        10 << scan
    )
