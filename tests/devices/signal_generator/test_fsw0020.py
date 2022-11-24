import pytest

from neclib.devices.signal_generator.fsw0020 import FSW0020

from ..conftest import get_instance

pytestmark = pytest.mark.skipif(
    get_instance(FSW0020) is None, reason="CPZ7415V is not configured"
)


class TestFSW0010:
    def test_config_type(self):
        sg = get_instance(FSW0020)
        assert type(sg.Config.host) is str
        assert type(sg.Config.port) is int
