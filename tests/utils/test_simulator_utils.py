from neclib import config
from neclib.utils import skip_on_simulator


def test_skip_on_simulator():
    @skip_on_simulator
    def test_func():
        return True

    config.simulator = True
    assert config.simulator
    assert test_func() is None

    config.simulator = False
    assert not config.simulator
    assert test_func()
