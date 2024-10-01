import pytest

from neclib.devices.motor.azd_ad import AZD_AD

from ..conftest import get_instance

pytestmark = pytest.mark.skipif(
    get_instance(AZD_AD) is None, reason="AZD_AD is not configured"
)


class TestAZD_AD:
    def test_config_type(self):
        motor = get_instance(AZD_AD)
        assert type(motor.Config.host) is str
        assert type(motor.Config.port) is int
        assert type(motor.Config.low_limit) is int
        assert type(motor.Config.high_limit) is int
