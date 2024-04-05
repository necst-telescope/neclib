import pytest

from neclib.devices.ccd_controller.m100 import M100

from ..conftest import get_instance

pytestmark = pytest.mark.skipif(
    get_instance(M100) is None, reason="M100 is not configured"
)


class TestM100:
    def test_config_type(self):
        ccd = get_instance(M100)
        assert type(ccd.Config.pic_captured_path) is str
