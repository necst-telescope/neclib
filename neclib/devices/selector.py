from types import ModuleType
from typing import Any, Dict, List

from .. import config, get_logger, utils
from ..exceptions import ConfigurationError

logger = get_logger(__name__)


def parse_device_configuration(modules: List[ModuleType]) -> Dict[str, Any]:
    implementations = list_implementations(modules)

    devices = config.dev
    if devices is None:
        return {}

    parsed = {}
    for k, v in devices.__dict__.items():
        if v.lower() in implementations.keys():
            parsed[k] = implementations[v.lower()]
            parsed[utils.toCamelCase(k)] = implementations[v.lower()]
        else:
            raise ConfigurationError(
                f"Driver implementation for device '{v}' ({k}) not found."
            )
    return parsed


def list_implementations(modules: List[ModuleType]) -> Dict[str, Any]:
    def list_implementations_single_module(module: ModuleType) -> Dict[str, Any]:
        impl = {}
        for attrname in dir(module):
            attr = getattr(module, attrname)
            if (
                hasattr(attr, "Model")
                and hasattr(attr, "Manufacturer")
                and callable(attr)
            ):
                impl[attrname.lower()] = attr

        return impl

    implementations = {}
    for module in modules:
        impl = list_implementations_single_module(module)
        implementations.update(impl)
    if len(implementations) != len(set(implementations.keys())):
        raise ValueError("Implemented device model isn't unique.")
    return implementations
