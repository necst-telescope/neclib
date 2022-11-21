from types import ModuleType
from typing import Dict, List, Type

from .. import config, get_logger, utils
from ..exceptions import ConfigurationError
from .device_base import DeviceBase

logger = get_logger(__name__)


def parse_device_configuration(
    modules: List[ModuleType],
) -> Dict[str, Type[DeviceBase]]:
    implementations = list_implementations(modules)

    devices = config.dev
    if devices is None:
        return {}

    parsed = {}
    for k, v in devices.items():
        if v.lower() in implementations.keys():
            impl = implementations[v.lower()]
            new: Type[DeviceBase] = type(
                utils.toCamelCase(k), (impl,), {}  # type: ignore
            )

            parsed[k] = parsed[utils.toCamelCase(k)] = new
            try:  # Instantiate once to ensure all configurations set.
                new().finalize()
            except Exception as e:
                logger.warning(f"Failed to initialize device {k}: {e}")
        else:
            raise ConfigurationError(
                f"Driver implementation for device '{v}' ({k}) not found."
            )
    return parsed


def list_implementations(modules: List[ModuleType]) -> Dict[str, DeviceBase]:
    def list_implementations_single_module(module: ModuleType) -> Dict[str, DeviceBase]:
        impl = {}
        for attrname in dir(module):
            attr = getattr(module, attrname)
            try:
                if issubclass(attr, DeviceBase):
                    impl[attrname.lower()] = attr
            except TypeError:
                del attr

        return impl

    implementations = {}
    for module in modules:
        impl = list_implementations_single_module(module)
        implementations.update(impl)
    if len(implementations) != len(set(implementations.keys())):
        raise ValueError("Implemented device model isn't unique.")
    return implementations
