import pytest

from neclib.devices.da_converter.cpz340816 import CPZ340816

from ..conftest import get_instance

pytestmark = pytest.mark.skipif(
    get_instance(CPZ340816) is None, reason="CPZ340816 is not configured"
)


class TestCPZ340816:
    def test_config_type(self):
        da_converter = get_instance(CPZ340816)
        assert type(da_converter.Config.rsw_id) is int
