# flake8: noqa

"""Pure Python tools for NECST."""

import logging
import sys
from importlib.metadata import version


try:
    __version__ = version("neclib")
except:
    __version__ = "0.0.0"  # Fallback.


logger = logging.getLogger("neclib")

if sys.platform != "linux":
    logger.warning(
        "Device drivers for Interface PCI boards are only supported on Linux."
    )

from .configuration import config, configure

config = config

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
