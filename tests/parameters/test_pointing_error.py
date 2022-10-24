import astropy.units as u
import pytest

from neclib.parameters import PointingError


class TestPointingError:
    def test_apparent2refracted(self, data_dir):
        calculator = PointingError.from_file(data_dir / "sample_pointing_param.toml")
        test_args = [
            (30, 60, {"unit": "deg"}),
            ([30, 30], [60, 60], {"unit": "deg"}),
            (30 * u.deg, 60 * u.deg, {}),
            ([30, 30] * u.deg, [60, 60] * u.deg, {}),
            (30 * u.deg, 60 * u.deg, {"unit": "arcsec"}),
        ]
        test_expected = [
            (31.48592499 * u.deg, 61.87403996 * u.deg),
            ([31.48592499, 31.48592499] * u.deg, [61.87403996, 61.87403996] * u.deg),
            (31.48592499 * u.deg, 61.87403996 * u.deg),
            ([31.48592499, 31.48592499] * u.deg, [61.87403996, 61.87403996] * u.deg),
            (31.48592499 * 3600 * u.arcsec, 61.87403996 * 3600 * u.arcsec),
        ]
        for (*args, kwargs), expected in zip(test_args, test_expected):
            actual = calculator.apparent2refracted(*args, **kwargs)
            assert actual[0].value == pytest.approx(expected[0].value)
            assert actual[1].value == pytest.approx(expected[1].value)

    def test_refracted2apparent(self, data_dir):
        calculator = PointingError.from_file(data_dir / "sample_pointing_param.toml")
        test_args = [
            (30, 60, {"unit": "deg"}),
            ([30, 30], [60, 60], {"unit": "deg"}),
            (30 * u.deg, 60 * u.deg, {}),
            ([30, 30] * u.deg, [60, 60] * u.deg, {}),
            (30 * u.deg, 60 * u.deg, {"unit": "arcsec"}),
        ]
        test_expected = [
            (28.51407501 * u.deg, 58.12596004 * u.deg),
            ([28.51407501, 28.51407501] * u.deg, [58.12596004, 58.12596004] * u.deg),
            (28.51407501 * u.deg, 58.12596004 * u.deg),
            ([28.51407501, 28.51407501] * u.deg, [58.12596004, 58.12596004] * u.deg),
            (28.51407501 * 3600 * u.arcsec, 58.12596004 * 3600 * u.arcsec),
        ]
        for (*args, kwargs), expected in zip(test_args, test_expected):
            actual = calculator.refracted2apparent(*args, **kwargs)
            assert actual[0].value == pytest.approx(expected[0].value)
            assert actual[1].value == pytest.approx(expected[1].value)
