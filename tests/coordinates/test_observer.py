import time

import astropy.units as u
import numpy as np
import pytest
from astropy.coordinates import LSR, EarthLocation, Longitude, SkyCoord
from astropy.time import Time

from neclib.coordinates import Observer
from neclib.coordinates.observer import get_v_bary


def get_v_obs(
    lon: float, lat: float, frame: str, unit: str, time: float, location: EarthLocation
) -> u.Quantity:
    _time = Time(time, format="unix")
    target = SkyCoord(lon, lat, frame=frame, unit=unit)
    LSR_frame = LSR(v_bary=get_v_bary())
    v_obs = SkyCoord(location.get_gcrs(_time)).transform_to(LSR_frame).velocity
    radial_velocity = (
        v_obs.d_x * np.cos(target.icrs.dec) * np.cos(target.icrs.ra)
        + v_obs.d_y * np.cos(target.icrs.dec) * np.sin(target.icrs.ra)
        + v_obs.d_z * np.sin(target.icrs.dec)
    )
    return radial_velocity


def get_lst(time: float, location: EarthLocation) -> Longitude:
    _time = Time(time, format="unix", location=location)
    return _time.sidereal_time("apparent")


def test_get_v_bary():
    actual = get_v_bary()
    assert actual.d_xyz.to_value("km/s") == pytest.approx(
        [10.27, 15.32, 7.74], abs=1e-2
    )


class TestObserver:
    def test_v_obs(self, location: EarthLocation):
        obs = Observer(location=location)
        kwargs = dict(lon=0.0, lat=0.0, frame="galactic", unit="deg", time=0.0)
        expected = get_v_obs(**kwargs, location=location)
        actual = obs.v_obs(**kwargs)
        assert actual.to_value("km/s") == pytest.approx(expected.to_value("km/s"))

    def test_lst(self, location: EarthLocation):
        obs = Observer(location=location)
        now = time.time()
        expected = get_lst(time=now, location=location)
        actual = obs.lst(time=now)
        assert actual.degree == pytest.approx(expected.degree)
