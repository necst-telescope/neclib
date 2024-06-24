import pytest

from neclib.devices.membrane.cpz2724 import CPZ2724

from ..conftest import get_instance

pytestmark = pytest.mark.skipif(
    get_instance(CPZ2724) is None, reason="CPZ2724 is not configured"
)


class TestCPZ3177:
    def test_config_type(self):
        membrane = get_instance(CPZ2724)
        assert type(membrane.Config.rsw_id) is int
