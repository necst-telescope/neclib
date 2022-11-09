"""Pure Python tools for NECST."""

import sys
from importlib.metadata import version


# Version Definition
try:
    __version__ = version("neclib")
except:  # noqa: E722
    __version__ = "0.0.0"  # Fallback.


# Environment Variables
class EnvVarName:
    necst_root: str = "NECST_ROOT"
    ros2_ws: str = "ROS2_WS"
    domain_id: str = "ROS_DOMAIN_ID"
    record_root: str = "NECST_RECORD_ROOT"


# Logger configuration
import logging  # noqa: E402

rootLogger = logging.getLogger()
rootLogger.setLevel(logging.DEBUG)
del logging


# Warn Restriction Imposed by Environment
from .interfaces import get_logger  # noqa: E402

logger = get_logger("neclib")
if sys.platform != "linux":
    logger.warning(
        "Device drivers for Interface PCI boards are only supported on Linux."
    )
del logger


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
from . import safety  # noqa: F401, E402
from . import simulators  # noqa: F401, E402
from . import utils  # noqa: F401, E402
