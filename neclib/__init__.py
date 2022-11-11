"""Pure Python tools for NECST."""


# Perform Time-consuming Downloads
class _TimeConsumingTasks:
    @staticmethod
    def download_astropy_parameter_files():
        """Will download finals2000A.all (3.4MB) and Leap_Second.dat (1.3KB)."""
        from astropy.time import Time

        Time.now().ut1


import concurrent.futures  # noqa: E402

executor = concurrent.futures.ThreadPoolExecutor()
futures = [
    executor.submit(getattr(_TimeConsumingTasks, func)())
    for func in dir(_TimeConsumingTasks)
    if not func.startswith("_")
]


# Logger configuration
import logging  # noqa: E402

rootLogger = logging.getLogger()
rootLogger.setLevel(logging.DEBUG)
del logging, rootLogger


# Version Definition
from importlib.metadata import version  # noqa: E402

try:
    __version__ = version("neclib")
except:  # noqa: E722
    __version__ = "0.0.0"  # Fallback.
del version


# Environment Variables
class EnvVarName:
    necst_root: str = "NECST_ROOT"
    ros2_ws: str = "ROS2_WS"
    domain_id: str = "ROS_DOMAIN_ID"
    record_root: str = "NECST_RECORD_ROOT"


# Warn Restriction Imposed by Environment
import sys  # noqa: E402
from .interfaces import get_logger  # noqa: E402

logger = get_logger("neclib")
if sys.platform != "linux":
    logger.warning(
        "Device drivers for Interface PCI boards are only supported on Linux."
    )
del logger, sys  # get_logger is intentionally kept in the namespace.


# Read Configuration
from .configuration import config, configure  # noqa: F401, E402


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


# Wait for all background tasks to complete.
concurrent.futures.wait(futures, timeout=60)
executor.shutdown()
del _TimeConsumingTasks, concurrent, executor, futures
