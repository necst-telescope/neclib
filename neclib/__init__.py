# flake8: noqa

"""Pure Python tools for NECST."""

try:
    from importlib.metadata import version  # Python 3.8+
except ImportError:
    from importlib_metadata import version

try:
    __version__ = version("neclib")
except:
    __version__ = "0.0.0"  # Fallback.

import logging

logger = logging.getLogger("neclib")

import sys

if sys.platform != "linux":
    logger.warning(
        "Device drivers for Interface PCI boards are only supported on Linux."
    )

# Aliases
from .exceptions import *

# Submodules
from . import typing
from . import units

# Subpackages
from . import controllers
from . import interfaces
from . import parameters
from . import simulators
from . import utils
