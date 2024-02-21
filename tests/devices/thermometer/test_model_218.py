import pytest

from neclib.devices.thermometer.model_218_usb import Model218USB

from ..conftest import get_instance

pytestmark = pytest.mark.skipif(
    get_instance(Model218USB) is None, reason="Model218 is not configured"
)


class TestModel218:
    def test_config_type(self):
        thermometer = get_instance(Model218USB)
        assert type(thermometer.Config.usb_port) is str
