from typing import Dict, Type, Union

from .. import config, get_logger, utils
from ..exceptions import NECSTConfigurationError
from .device_base import DeviceBase, DeviceMapping, get_device_list

logger = get_logger(__name__)


def get_device_configuration() -> Dict[str, Union[str, Dict[str, str]]]:
    devices = {k[:-2]: v for k, v in config.items() if k.endswith("._")}
    device_kinds = set(d.split(".")[0] for d in devices)
    parsed = {}
    for kind in device_kinds:
        if kind in devices:
            parsed[kind] = devices[kind]
        else:
            prefix_length = len(f"{kind}.")
            parsed[kind] = {
                k[prefix_length:]: v for k, v in devices.items() if k.startswith(kind)
            }
    return parsed


def parse_device_configuration() -> Dict[str, Union[DeviceBase, DeviceMapping]]:
    configuration = get_device_configuration()
    implementations = {}
    for k, v in configuration.items():
        try:
            implementations[k] = DeviceBase(name=k, model=v)
            implementations[utils.toCamelCase(k)] = implementations[k]
        except Exception:
            raise NECSTConfigurationError(
                f"Driver implementation for device '{v}' ({k}) not found."
            )
    return implementations


def list_implementations() -> Dict[str, Type[DeviceBase]]:
    return get_device_list()
