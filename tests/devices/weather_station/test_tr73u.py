import pytest

from neclib.devices.weather_station.tr73u import TR73U

from ..conftest import get_instance

pytestmark = pytest.mark.skipif(
    get_instance(TR73U) is None, reason="TR73U is not configured"
)


class TestModel218:
    def test_config_type(self):
        thermometer = get_instance(TR73U)
        assert type(thermometer.Config.port) is str  # Path is not accepted
