import pytest

from neclib.devices.spectrometer.xffts import XFFTS

from ..conftest import get_instance

pytestmark = pytest.mark.skipif(
    get_instance(XFFTS) is None, reason="XFFTS is not configured"
)


class TestXFFTS:
    def test_config_type(self):
        spectrometer = get_instance(XFFTS)
        assert type(spectrometer.Config.host) is str
        assert type(spectrometer.Config.data_port) is int
        assert type(spectrometer.Config.cmd_port) is int
        assert type(spectrometer.Config.synctime_us) is int
        assert type(spectrometer.Config.max_ch) is int
