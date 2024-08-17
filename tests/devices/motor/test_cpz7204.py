import pytest

from neclib.devices.motor.cpz7204 import CPZ7204

from ..conftest import get_instance

pytestmark = pytest.mark.skipif(
    get_instance(CPZ7204) is None, reason="CPZ7204 is not configured"
)


class TestCPZ7204:
    def test_config_type(self):
        motor = get_instance(CPZ7204)
        assert type(motor.Config.rsw_id) is int
