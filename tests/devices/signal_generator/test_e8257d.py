import pytest

from neclib.devices.signal_generator.e8257d import E8257D

from ..conftest import get_instance

pytestmark = pytest.mark.skipif(
    get_instance(E8257D) is None, reason="E8257D is not configured"
)


class TestML2437A:
    def test_config_type(self):
        sg = get_instance(E8257D)
        assert type(sg.Config.communicator) is str
        assert type(sg.Config.host) is str
