import astropy.units as u
import pytest

from neclib.parameters import PointingError


class TestPointingError:
    def test_encoder2refracted(self, data_dir):
        calculator = PointingError.from_file(data_dir / "example_pointing_param.toml")
        test_args = [
            (30, 60, {"unit": "deg"}),
            ([30, 30], [60, 60], {"unit": "deg"}),
            (30 * u.deg, 60 * u.deg, {}),
            ([30, 30] * u.deg, [60, 60] * u.deg, {}),
            (30 * u.deg, 60 * u.deg, {"unit": "arcsec"}),
        ]
        test_expected = [
            (31.48592499 * u.deg, 62.01728925 * u.deg),
            ([31.48592499, 31.48592499] * u.deg, [62.01728925, 62.01728925] * u.deg),
            (31.48592499 * u.deg, 62.01728925 * u.deg),
            ([31.48592499, 31.48592499] * u.deg, [62.01728925, 62.01728925] * u.deg),
            (31.48592499 * 3600 * u.arcsec, 62.01728925 * 3600 * u.arcsec),
        ]
        for (*args, kwargs), expected in zip(test_args, test_expected):
            actual = calculator.encoder2refracted(*args, **kwargs)
            assert actual[0].value == pytest.approx(expected[0].value)
            assert actual[1].value == pytest.approx(expected[1].value)

    def test_refracted2encoder(self, data_dir):
        calculator = PointingError.from_file(data_dir / "example_pointing_param.toml")
        test_args = [
            (30, 60, {"unit": "deg"}),
            ([30, 30], [60, 60], {"unit": "deg"}),
            (30 * u.deg, 60 * u.deg, {}),
            ([30, 30] * u.deg, [60, 60] * u.deg, {}),
            (30 * u.deg, 60 * u.deg, {"unit": "arcsec"}),
        ]
        test_expected = [
            (28.51407501 * u.deg, 57.98271075 * u.deg),
            ([28.51407501, 28.51407501] * u.deg, [57.98271075, 57.98271075] * u.deg),
            (28.51407501 * u.deg, 57.98271075 * u.deg),
            ([28.51407501, 28.51407501] * u.deg, [57.98271075, 57.98271075] * u.deg),
            (28.51407501 * 3600 * u.arcsec, 57.98271075 * 3600 * u.arcsec),
        ]
        for (*args, kwargs), expected in zip(test_args, test_expected):
            actual = calculator.refracted2encoder(*args, **kwargs)
            assert actual[0].value == pytest.approx(expected[0].value)
            assert actual[1].value == pytest.approx(expected[1].value)
