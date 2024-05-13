"""Device controllers.

NECLIB highly abstracts the devices to their *kind*, say "motor", "spectrometer", and so
on. This will allow users to write a code without model-specific configuration process
and even complete reuse of the code on device replacement. The model-specific
configurations should be stored in ``neclib.config`` object.

"""

import importlib
import sys
from pathlib import Path
from types import ModuleType
from typing import Dict, Type

from ..core import get_logger
from . import selector
from .device_base import DeviceBase, Devices

# Warn system-dependent implementations
if not sys.platform.startswith("linux"):
    logger = get_logger(__file__)
    logger.warning(
        "Device drivers for Interface PCI boards are only supported on Linux."
    )

# Find and import all device controller implementations, for subclass search in
# `device_base.get_device_list()`
paths = Path(__file__).parent.iterdir()
module_paths = filter(lambda p: p.is_dir() and p.name[0] not in "._", paths)
impl_modules = [
    importlib.import_module(f".{m.name}", __package__) for m in module_paths
]

implementations: Dict[str, Type[DeviceBase]]
"""List of all available implementations."""

parsed: Dict[str, Devices] = {}
"""List of parsed device implementations."""

here = sys.modules[__name__]


def reload():
    global implementations, parsed
    [delattr(here, k) for k in parsed.keys()]
    implementations = selector.list_implementations()
    parsed = selector.parse_device_configuration()
    for k, v in parsed.items():
        if (not hasattr(here, k)) or isinstance(getattr(here, k), ModuleType):
            setattr(here, k, v)
        else:
            logger = get_logger(__file__)
            logger.warning(f"Cannot set name {k!r}; already defined in this module.")


reload()
