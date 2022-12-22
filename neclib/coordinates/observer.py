__all__ = ["Observer"]

import time as pytime
from functools import lru_cache
from typing import Optional, Sequence, Union

import astropy.units as u
from astropy.coordinates import LSR, CartesianDifferential, EarthLocation, SkyCoord
from astropy.time import Time

from ..typing import CoordFrameType, QuantityValue, UnitType


@lru_cache
def get_v_bary():
    """Barycentric velocity of the sun relative to the LSR; towards the solar apex."""
    SolarApex = SkyCoord(
        ra="18h",
        dec="30d",
        frame="fk4",
        equinox=Time("B1900"),
    )
    v_sun = 20 * u.km / u.s * SolarApex.galactic.cartesian
    U, V, W = v_sun.x, v_sun.y, v_sun.z
    print(U, V, W)
    v_bary = CartesianDifferential(U, V, W)
    return v_bary


class Observer:
    def __init__(self, location: EarthLocation):
        self.location = location

    def v_obs(
        self,
        lon: QuantityValue,
        lat: QuantityValue,
        frame: CoordFrameType,
        unit: Optional[UnitType] = None,
        time: Optional[float] = None,
    ) -> u.Quantity:
        time = pytime.time() if time is None else time
        unit = getattr(lon, "unit", None) if unit is None else unit
        unit = getattr(lat, "unit", "") if unit is None else unit

        time = Time(time, format="unix")
        target = SkyCoord(lon, lat, frame=frame, unit=unit)
        LSR_frame = LSR(v_bary=get_v_bary())
        v_obs = SkyCoord(self.location.get_gcrs(time)).transform_to(LSR_frame).velocity
        radial_velocity = v_obs.to_cartesian(target.cartesian).x
        return radial_velocity

    def lst(self, time: Optional[Union[float, Sequence[float]]] = None) -> Time:
        time = pytime.time() if time is None else time
        time = Time(time, format="unix", location=self.location)
        return time.sidereal_time("apparent")
