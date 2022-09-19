from types import ModuleType
from typing import Any, Dict, List

from neclib import config, logger
from ..exceptions import ConfigurationError


def parse_device_configuration(modules: List[ModuleType]):
    implementations = list_implementations(modules)

    devices = config.dev
    if devices is None:
        raise ConfigurationError("No device configuration found.")

    parsed = {}
    for k, v in devices.__dict__.items():
        if v.lower() in implementations.keys():
            parsed[k] = implementations[v.lower()]
        else:
            logger.warning(f"Driver implementation for device '{v}' ({k}) not found.")
    return parsed


def list_implementations(modules: List[ModuleType]) -> Dict[str, Any]:
    implementations = {}
    for module in modules:
        impl = _find_implementations(module)
        implementations.update(impl)
    return implementations


def _find_implementations(module: ModuleType) -> Dict[str, Any]:
    impl = {}
    for attrname in dir(module):
        attr = getattr(module, attrname)
        if hasattr(attr, "Model") and callable(attr):
            impl[attrname.lower()] = attr

    return impl
