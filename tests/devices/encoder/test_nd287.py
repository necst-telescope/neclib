import pytest

from neclib.devices.encoder import ND287

from ..conftest import get_instance

pytestmark = pytest.mark.skipif(
    get_instance(ND287) is None, reason="ND287 is not configured"
)


class TestND287:
    def test_config_type(self) -> None:
        encoder = get_instance(ND287)
        assert type(encoder.Config.port_az) in (str, type(None))  # Path is not accepted
        assert type(encoder.Config.port_el) in (str, type(None))
