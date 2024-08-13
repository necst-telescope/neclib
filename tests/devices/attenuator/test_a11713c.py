import pytest

from neclib.devices.attenuator.a11713c import A11713C

from ..conftest import get_instance

pytestmark = pytest.mark.skipif(
    get_instance(A11713C) is None, reason="11713C is not configured"
)


class TestA11713B:
    def test_config_type(self):
        attenuator = get_instance(A11713C)
        assert type(attenuator.Config.communicator) is str
        assert type(attenuator.Config.host) is str
        assert type(attenuator.Config.model) is str
