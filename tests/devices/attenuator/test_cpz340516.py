import pytest

from neclib.devices.attenuator.cpz340516 import CPZ340516

from ..conftest import get_instance

pytestmark = pytest.mark.skipif(
    get_instance(CPZ340516) is None, reason="cpz340516 is not configured"
)


class TestRhio10:
    def test_config_type(self):
        attenuator = get_instance(CPZ340516)
        assert type(attenuator.Config.rsw_id) is int
        assert type(attenuator.Config.range) is str
        assert type(attenuator.Config.channel) is str
