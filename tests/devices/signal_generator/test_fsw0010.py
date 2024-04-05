import pytest

from neclib.devices.signal_generator.fsw0010 import FSW0010

from ..conftest import get_instance

pytestmark = pytest.mark.skipif(
    get_instance(FSW0010) is None, reason="FSW0010 is not configured"
)


class TestFSW0010:
    def test_config_type(self):
        sg = get_instance(FSW0010)
        assert type(sg.Config.host) is str
        assert type(sg.Config.port) is int
