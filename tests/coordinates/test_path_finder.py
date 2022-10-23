import astropy.constants as const
import astropy.units as u
import pytest
from astropy.coordinates import AltAz, EarthLocation, FK5

from neclib.coordinates import PathFinder


class TestPathFinder:

    location = EarthLocation("138.472153deg", "35.940874deg", "1386m")
    pressure = 850 * u.hPa
    temperature = 290 * u.K
    relative_humidity = 0.5
    obswl = const.c / (230*u.GHz)
    obsfreq = 230 * u.GHz
    obstime = 1000

    def test_01(self, data_dir):
        pointing_param_path = data_dir / "sample_pointing_param.toml"
        finder = PathFinder(
            location = self.location,
            pointing_param_path = pointing_param_path,
            pressure = self.pressure,
            temperature = self.temperature,
            relative_humidity = self.relative_humidity,
            obswl = self.obswl,
        )
        assert finder.linear(
            start = (0, 0),
            end = (0.05, 0),
            frame = AltAz,
            speed = 0.5,
            unit = u.deg,
            obstime = self.obstime,
        ) == (
            [0, 0.01, 0.02, 0.03, 0.04, 0.05] * u.deg,
            [0, 0, 0, 0, 0, 0] * u.deg,
            [1000, 1000.02, 1000.04, 1000.06, 1000.08, 1000.1],
        )