from neclib import config, devices
from neclib.utils import toCamelCase


class TestSelector:
    def test_camelcase_import(self):
        configured_devices = {
            k.split("::")[0]: v for k, v in config.items() if k.endswith("::_")
        }
        for k, v in configured_devices.items():
            name = toCamelCase(k)
            assert v in repr(getattr(devices, name))

    def test_snakecase_import(self):
        configured_devices = {
            k.split("::")[0]: v for k, v in config.items() if k.endswith("::_")
        }
        for name, v in configured_devices.items():
            assert v in repr(getattr(devices, name))
