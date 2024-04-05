import pytest

from neclib.devices.power_meter.ma24126a import MA24126A

from ..conftest import get_instance

pytestmark = pytest.mark.skipif(
    get_instance(MA24126A) is None, reason="MA24126A is not configured"
)


class TestMA24126A:
    def test_config_type(self):
        power_meter = get_instance(MA24126A)
        assert type(power_meter.Config.port) is str
