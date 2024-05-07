import pytest

from neclib.devices.power_meter.ml2437a import ML2437A

from ..conftest import get_instance

pytestmark = pytest.mark.skipif(
    get_instance(ML2437A) is None, reason="ML2437A is not configured"
)


class TestML2437A:
    def test_config_type(self):
        power_meter = get_instance(ML2437A)
        assert type(power_meter.Config.host) is str
        assert type(power_meter.Config.port) is int
