import pytest

from neclib.devices.motor.cpz2724 import CPZ2724

from ..conftest import get_instance

pytestmark = pytest.mark.skipif(
    get_instance(CPZ2724) is None, reason="CPZ2724 is not configured"
)


class TestCPZ2724:
    def test_config_type(self):
        motor = get_instance(CPZ2724)
        assert type(motor.Config.rsw_id) is int
