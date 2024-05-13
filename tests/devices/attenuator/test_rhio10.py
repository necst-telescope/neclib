import pytest

from neclib.devices.attenuator.rhio10 import RHIO10

from ..conftest import get_instance

pytestmark = pytest.mark.skipif(
    get_instance(RHIO10) is None, reason="rhio10 is not configured"
)


class TestRhio10:
    def test_config_type(self):
        attenuator = get_instance(RHIO10)
        assert type(attenuator.Config.host) is str
        assert type(attenuator.Config.port) is int
