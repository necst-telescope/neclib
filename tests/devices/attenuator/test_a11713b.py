import pytest

from neclib.devices.attenuator.a11713b import A11713B

from ..conftest import get_instance

pytestmark = pytest.mark.skipif(
    get_instance(A11713B) is None, reason="11713B is not configured"
)


class TestA11713B:
    def test_config_type(self):
        attenuator = get_instance(A11713B)
        assert type(attenuator.Config.communicator) is str
        assert type(attenuator.Config.host) is str
        assert type(attenuator.Config.model) is str
