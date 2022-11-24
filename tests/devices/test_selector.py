from neclib import config, devices
from neclib.utils import toCamelCase


class TestSelector:
    def test_camelcase_import(self):
        for k, v in config.dev.items():
            name = toCamelCase(k)
            assert getattr(devices, name).Model == v

    def test_snakecase_import(self):
        for name, v in config.dev.items():
            assert getattr(devices, name).Model == v
