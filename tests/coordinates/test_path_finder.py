import time

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
    obswl = const.c / (230 * u.GHz)
    obsfreq = 230 * u.GHz
    obstime = 1000

    def test_01(self, data_dir):
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
        az, el, t = finder.linear(
            start=(0, 0),
            end=(0.05, 0),
            frame=AltAz,
            speed=0.5,
            unit=u.deg,
            # obstime = self.obstime,
        )
        assert (az == [0, 0.01, 0.02, 0.03, 0.04, 0.05] * u.deg).all()
        assert (el == [0, 0, 0, 0, 0, 0] * u.deg).all()
        assert (
            t
            == pytest.approx(
                [now + 3, now + 3.02, now + 3.04, now + 3.06, now + 3.08, now + 3.1]
            )
        ).all()
