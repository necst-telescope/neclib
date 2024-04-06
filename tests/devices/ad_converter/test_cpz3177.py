import pytest

from neclib.devices.ad_converter.cpz3177 import CPZ3177

from ..conftest import get_instance

pytestmark = pytest.mark.skipif(
    get_instance(CPZ3177) is None, reason="CPZ3177 is not configured"
)


class TestCPZ3177:
    def test_config_type(self):
        ad_converter = get_instance(CPZ3177)
        assert type(ad_converter.Config.rsw_id) is int
        assert type(ad_converter.Config.ave_num) is int
        assert type(ad_converter.Config.smpl_freq) is int
        assert type(ad_converter.Config.single_diff) is str
        assert type(ad_converter.Config.all_ch_num) is int
        assert type(ad_converter.Config.ch_range) is str
