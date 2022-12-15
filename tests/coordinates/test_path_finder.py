import time

import astropy.constants as const
import astropy.units as u
import numpy as np
import pytest
from astropy.coordinates import FK5, AltAz, EarthLocation
from astropy.time import Time

from neclib.coordinates import CoordCalculator, PathFinder, standby_position


class TestStandbyPosition:
    def test_along_longitude(self):
        actual = standby_position(start=(30, 50), end=(32, 50), unit="deg", margin=0.5)
        assert actual == (29.5 * u.deg, 50 * u.deg)

    def test_along_longitude_quantity(self):
        actual = standby_position(
            start=(30 * u.deg, 50 * u.deg),
            end=(32 * u.deg, 50 * u.deg),
            margin=0.5 * u.deg,
        )
        assert actual == (29.5 * u.deg, 50 * u.deg)

    def test_along_latitude(self):
        actual = standby_position(
            start=(-7200, 0), end=(-7200, -3600), unit="arcsec", margin=1800
        )
        assert actual == (-7200 * u.arcsec, 1800 * u.arcsec)


class TestPathFinder:

    location = EarthLocation("138.472153deg", "35.940874deg", "1386m")
    pressure = 850 * u.hPa
    temperature = 290 * u.K
    relative_humidity = 0.5
    obswl = const.c / (230 * u.GHz)
    obsfreq = 230 * u.GHz

    def _get_expected_value(self, pointing_param_path, lon, lat, frame, unit, obstime):
        calculator = CoordCalculator(
            location=self.location,
            pointing_param_path=pointing_param_path,
            pressure=self.pressure,
            temperature=self.temperature,
            relative_humidity=self.relative_humidity,
            obsfreq=self.obsfreq,
        )
        az, el, _ = calculator.get_altaz(
            lon=lon,
            lat=lat,
            frame=frame,
            unit=unit,
            obstime=obstime,
        )
        return az, el, obstime

    def test_from_zero(self, data_dir):
        pointing_param_path = data_dir / "sample_pointing_param.toml"
        finder = PathFinder(
            location=self.location,
            pointing_param_path=pointing_param_path,
            pressure=self.pressure,
            temperature=self.temperature,
            relative_humidity=self.relative_humidity,
            obswl=self.obswl,
        )
        result = finder.linear(
            start=(0, 0), end=(0.05, 0), frame="altaz", speed=0.5, unit=u.deg
        )
        az, el, t = next(result)
        expected_az, expected_el, expected_t = self._get_expected_value(
            pointing_param_path=pointing_param_path,
            lon=[0, 0.01, 0.02, 0.03, 0.04, 0.05],
            lat=[0, 0, 0, 0, 0, 0],
            frame="altaz",
            unit=u.deg,
            obstime=t,
        )
        assert az.value == pytest.approx(expected_az.value)
        assert az.unit == expected_az.unit
        assert el.value == pytest.approx(expected_el.value)
        assert el.unit == expected_el.unit
        assert t == pytest.approx(expected_t)

    def test_quantity_input(self, data_dir):
        pointing_param_path = data_dir / "sample_pointing_param.toml"
        finder = PathFinder(
            location=self.location,
            pointing_param_path=pointing_param_path,
            pressure=self.pressure,
            temperature=self.temperature,
            relative_humidity=self.relative_humidity,
            obswl=self.obswl,
        )
        now = time.time()
        result = finder.linear(
            start=(0 * u.arcsec, 0 * u.arcsec),
            end=(180 * u.arcsec, 0 * u.arcsec),
            frame=AltAz(
                obstime=Time(
                    [
                        now + 3,
                        now + 3.02,
                        now + 3.04,
                        now + 3.06,
                        now + 3.08,
                        now + 3.1,
                    ],
                    format="unix",
                ),
                location=self.location,
                pressure=self.pressure,
                temperature=self.temperature.to("deg_C", equivalencies=u.temperature()),
                relative_humidity=self.relative_humidity,
                obswl=self.obswl,
            ),
            speed=30 * u.arcmin / u.second,
            unit=None,
        )
        az, el, t = next(result)
        expected_az, expected_el, expected_t = self._get_expected_value(
            pointing_param_path=pointing_param_path,
            lon=[0, 36, 72, 108, 144, 180],
            lat=[0, 0, 0, 0, 0, 0],
            frame="altaz",
            unit=u.arcsec,
            obstime=t,
        )
        assert az.value == pytest.approx(expected_az.value)
        assert az.unit == expected_az.unit
        assert el.value == pytest.approx(expected_el.value)
        assert el.unit == expected_el.unit
        assert t == pytest.approx(expected_t)

    def test_x_scan_fk5_plus(self, data_dir):
        pointing_param_path = data_dir / "sample_pointing_param.toml"
        finder = PathFinder(
            location=self.location,
            pointing_param_path=pointing_param_path,
            pressure=self.pressure,
            temperature=self.temperature,
            relative_humidity=self.relative_humidity,
            obswl=self.obswl,
        )

        result = finder.linear(
            start=(10, 20),
            end=(13, 20),
            frame="fk5",
            speed=10,
            unit=u.arcmin,
        )
        az, el, t = next(result)
        expected_az, expected_el, expected_t = self._get_expected_value(
            pointing_param_path=pointing_param_path,
            lon=[10 + i * 0.2 for i in range(16)],
            lat=[20 for i in range(16)],
            frame="fk5",
            unit=u.arcmin,
            obstime=t,
        )
        assert az.value == pytest.approx(expected_az.value)
        assert az.unit == expected_az.unit
        assert el.value == pytest.approx(expected_el.value)
        assert el.unit == expected_el.unit
        assert t == pytest.approx(expected_t)

    def test_x_scan_fk5_minus(self, data_dir):
        pointing_param_path = data_dir / "sample_pointing_param.toml"
        finder = PathFinder(
            location=self.location,
            pointing_param_path=pointing_param_path,
            pressure=self.pressure,
            temperature=self.temperature,
            relative_humidity=self.relative_humidity,
            obswl=self.obswl,
        )

        result = finder.linear(
            start=(-10, 20),
            end=(-13, 20),
            frame="fk5",
            speed=10,
            unit=u.arcmin,
        )
        az, el, t = next(result)
        expected_az, expected_el, expected_t = self._get_expected_value(
            pointing_param_path=pointing_param_path,
            lon=[-10 - i * 0.2 for i in range(16)],
            lat=[20 for i in range(16)],
            frame="fk5",
            unit=u.arcmin,
            obstime=t,
        )
        assert az.value == pytest.approx(expected_az.value)
        assert az.unit == expected_az.unit
        assert el.value == pytest.approx(expected_el.value)
        assert el.unit == expected_el.unit
        assert t == pytest.approx(expected_t)

    def test_y_scan_fk5_plus(self, data_dir):
        pointing_param_path = data_dir / "sample_pointing_param.toml"
        finder = PathFinder(
            location=self.location,
            pointing_param_path=pointing_param_path,
            pressure=self.pressure,
            temperature=self.temperature,
            relative_humidity=self.relative_humidity,
            obswl=self.obswl,
        )

        result = finder.linear(
            start=(10, 20),
            end=(10, 23),
            frame="fk5",
            speed=10,
            unit=u.arcmin,
        )
        az, el, t = next(result)
        expected_az, expected_el, expected_t = self._get_expected_value(
            pointing_param_path=pointing_param_path,
            lon=[10 for i in range(16)],
            lat=[20 + i * 0.2 for i in range(16)],
            frame="fk5",
            unit=u.arcmin,
            obstime=t,
        )
        assert az.value == pytest.approx(expected_az.value)
        assert az.unit == expected_az.unit
        assert el.value == pytest.approx(expected_el.value)
        assert el.unit == expected_el.unit
        assert t == pytest.approx(expected_t)

    def test_y_scan_fk5_minus(self, data_dir):
        pointing_param_path = data_dir / "sample_pointing_param.toml"
        finder = PathFinder(
            location=self.location,
            pointing_param_path=pointing_param_path,
            pressure=self.pressure,
            temperature=self.temperature,
            relative_humidity=self.relative_humidity,
            obswl=self.obswl,
        )
        result = finder.linear(
            start=(-10, 1.5),
            end=(-10, -1.5),
            frame="fk5",
            speed=10,
            unit=u.arcmin,
        )
        az, el, t = next(result)
        expected_az, expected_el, expected_t = self._get_expected_value(
            pointing_param_path=pointing_param_path,
            lon=[-10 for _ in range(16)],
            lat=[1.5 - i * 0.2 for i in range(16)],
            frame="fk5",
            unit=u.arcmin,
            obstime=t,
        )
        assert az.value == pytest.approx(expected_az.value)
        assert az.unit == expected_az.unit
        assert el.value == pytest.approx(expected_el.value)
        assert el.unit == expected_el.unit
        assert t == pytest.approx(expected_t)

    def test_y_scan_altaz_minus(self, data_dir):
        pointing_param_path = data_dir / "sample_pointing_param.toml"
        finder = PathFinder(
            location=self.location,
            pointing_param_path=pointing_param_path,
            pressure=self.pressure,
            temperature=self.temperature,
            relative_humidity=self.relative_humidity,
            obswl=self.obswl,
        )

        result = finder.linear(
            start=(-10, -20),
            end=(-10, -23),
            frame="altaz",
            speed=10,
            unit=u.arcmin,
        )
        az, el, t = next(result)
        expected_az, expected_el, expected_t = self._get_expected_value(
            pointing_param_path=pointing_param_path,
            lon=[-10 for _ in range(16)],
            lat=[-20 - i * 0.2 for i in range(16)],
            frame="altaz",
            unit=u.arcmin,
            obstime=t,
        )
        assert az.value == pytest.approx(expected_az.value)
        assert az.unit == expected_az.unit
        assert el.value == pytest.approx(expected_el.value)
        assert el.unit == expected_el.unit
        assert t == pytest.approx(expected_t)

    def test_over_end_position(self, data_dir):
        pointing_param_path = data_dir / "sample_pointing_param.toml"
        finder = PathFinder(
            location=self.location,
            pointing_param_path=pointing_param_path,
            pressure=self.pressure,
            temperature=self.temperature,
            relative_humidity=self.relative_humidity,
            obswl=self.obswl,
        )

        result = finder.linear(
            start=(10, 20),
            end=(12.9, 20),
            frame="fk5",
            speed=10,
            unit=u.arcmin,
        )
        az, el, t = next(result)
        expected_az, expected_el, expected_t = self._get_expected_value(
            pointing_param_path=pointing_param_path,
            lon=[10 + i * 0.2 for i in range(15)] + [12.9],
            lat=[20 for _ in range(16)],
            frame="fk5",
            unit=u.arcmin,
            obstime=t,
        )
        assert az.value == pytest.approx(expected_az.value)
        assert az.unit == expected_az.unit
        assert el.value == pytest.approx(expected_el.value)
        assert el.unit == expected_el.unit
        assert t == pytest.approx(expected_t)

    def test_few_output(self, data_dir):
        pointing_param_path = data_dir / "sample_pointing_param.toml"
        finder = PathFinder(
            location=self.location,
            pointing_param_path=pointing_param_path,
            pressure=self.pressure,
            temperature=self.temperature,
            relative_humidity=self.relative_humidity,
            obswl=self.obswl,
        )
        result = finder.linear(
            start=(10, 20),
            end=(10.2, 20),
            frame="fk5",
            speed=10,
            unit=u.arcmin,
        )
        az, el, t = next(result)
        expected_az, expected_el, expected_t = self._get_expected_value(
            pointing_param_path=pointing_param_path,
            lon=[10, 10.2],
            lat=[20, 20],
            frame="fk5",
            unit=u.arcmin,
            obstime=t,
        )
        assert az.value == pytest.approx(expected_az.value)
        assert az.unit == expected_az.unit
        assert el.value == pytest.approx(expected_el.value)
        assert el.unit == expected_el.unit
        assert t == pytest.approx(expected_t)

    def test_many_output(self, data_dir):
        pointing_param_path = data_dir / "sample_pointing_param.toml"
        finder = PathFinder(
            location=self.location,
            pointing_param_path=pointing_param_path,
            pressure=self.pressure,
            temperature=self.temperature,
            relative_humidity=self.relative_humidity,
            obswl=self.obswl,
        )

        result = finder.linear(
            start=(1.85, 45),
            end=(4, 45),
            frame=FK5,
            speed=1 / 2,
            unit=u.arcmin,
        )
        az, el, t = next(result)
        for _az, _el, _t in result:
            az = np.r_[az, _az]
            el = np.r_[el, _el]
            t = np.r_[t, _t]
        expected_az, expected_el, expected_t = self._get_expected_value(
            pointing_param_path=pointing_param_path,
            lon=[1.85 + i * 0.01 for i in range(216)],
            lat=[45 for _ in range(216)],
            frame="fk5",
            unit=u.arcmin,
            obstime=t,
        )
        assert az.value == pytest.approx(expected_az.value)
        assert az.unit == expected_az.unit
        assert el.value == pytest.approx(expected_el.value)
        assert el.unit == expected_el.unit
        assert t == pytest.approx(expected_t)

    def test_track(self, data_dir):
        pointing_param_path = data_dir / "sample_pointing_param.toml"
        finder = PathFinder(
            location=self.location,
            pointing_param_path=pointing_param_path,
            pressure=self.pressure,
            temperature=self.temperature,
            relative_humidity=self.relative_humidity,
            obswl=self.obswl,
        )
        result = finder.track(
            lon=30,
            lat=45,
            frame=FK5,
            unit="deg",
        )
        az, el, t = next(result)
        for _ in range(5):
            _az, _el, _t = next(result)
            az = np.r_[az, _az]
            el = np.r_[el, _el]
            t = np.r_[t, _t]
        expected_az, expected_el, expected_t = self._get_expected_value(
            pointing_param_path=pointing_param_path,
            lon=30,
            lat=45,
            frame="fk5",
            unit=u.deg,
            obstime=t,
        )
        assert az.value == pytest.approx(expected_az.value)
        assert az.unit == expected_az.unit
        assert el.value == pytest.approx(expected_el.value)
        assert el.unit == expected_el.unit
        assert t == pytest.approx(expected_t)
