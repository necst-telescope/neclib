from astropy import units as u
from pytest import approx

from neclib import config
from neclib.coordinates import PointingError

from ...conftest import configured_tester_factory


class TestOMU1P85M(configured_tester_factory("config_default")):
    def test_mutual_offset(self):
        pe = PointingError.from_file(config.antenna.pointing_parameter_path)
        az0, el0 = 25 * u.deg, 25 * u.deg
        azdash, eldash, dAz, dEl = pe.refracted_to_apparent(az0, el0)
        az0_mutual, el0_mutual = pe.apparent_to_refracted(azdash, eldash)
        assert az0.value == approx(az0_mutual.value)
        assert el0.value == approx(el0_mutual.value)
        assert azdash - dAz == az0
        assert eldash - dEl == el0
