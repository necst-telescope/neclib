import pytest

from neclib.devices.thermometer.model_218 import Model218

from ..conftest import get_instance

pytestmark = pytest.mark.skipif(
    get_instance(Model218) is None, reason="Model218 is not configured"
)


class TestModel218:
    def test_config_type(self):
        thermometer = get_instance(Model218)
        assert type(thermometer.Config.host) is str
        assert type(thermometer.Config.port) is int
