import pytest

from neclib.devices.encoder.cpz6204 import CPZ6204

from ..conftest import get_instance

pytestmark = pytest.mark.skipif(
    get_instance(CPZ6204) is None, reason="CPZ6204 is not configured"
)


class TestCPZ6204:
    def test_config_type(self):
        ad_converter = get_instance(CPZ6204)
        assert type(ad_converter.Config.rsw_id) is int
