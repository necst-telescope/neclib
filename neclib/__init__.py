"""Pure Python tools for NECST."""

import logging
import sys
from importlib.metadata import version


# Version Definition

try:
    __version__ = version("neclib")
except:  # noqa: E722
    __version__ = "0.0.0"  # Fallback.


# Warn Restriction Imposed by Environment

logger = logging.getLogger("neclib")  # TODO: Use custom console_logger.
if sys.platform != "linux":
    logger.warning(
        "Device drivers for Interface PCI boards are only supported on Linux."
    )
# del logger  # TODO: Remove loggers refers to this.


# Read Configuration

from .configuration import config, configure  # noqa: F401, E402

config = config


# Perform Time-consuming Downloads

from astropy.time import Time  # noqa: E402

_ = Time.now().ut1  # Will download finals2000A.all (3.4MB) and Leap_Second.dat (1.3KB).
del Time


# Aliases

from .exceptions import *  # noqa: F401, E402, F403


# Submodules

from . import typing  # noqa: F401, E402
from . import units  # noqa: F401, E402


# Subpackages

from . import controllers  # noqa: F401, E402
from . import interfaces  # noqa: F401, E402
from . import parameters  # noqa: F401, E402
from . import recorders  # noqa: F401, E402
from . import simulators  # noqa: F401, E402
from . import utils  # noqa: F401, E402
