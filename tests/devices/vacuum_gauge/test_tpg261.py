import pytest

from neclib.devices.vacuum_gauge.tpg261 import TPG261

from ..conftest import get_instance

pytestmark = pytest.mark.skipif(
    get_instance(TPG261) is None, reason="TPG261 is not configured"
)


class TestTPG261:
    def test_config_type(self):
        vacuum_gauge = get_instance(TPG261)
        assert type(vacuum_gauge.Config.communicator) is str
