import pytest

from neclib.devices.signal_generator.mg3692c import MG3692C

from ..conftest import get_instance

pytestmark = pytest.mark.skipif(
    get_instance(MG3692C) is None, reason="MG3692C is not configured"
)


class TestML2437A:
    def test_config_type(self):
        sg = get_instance(MG3692C)
        assert type(sg.Config.host) is str
        assert type(sg.Config.port) is int
