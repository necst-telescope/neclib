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
    executor.submit(getattr(_TimeConsumingTasks, func))
    for func in dir(_TimeConsumingTasks)
    if not func.startswith("_")
]


# Logger configuration
import logging  # noqa: E402

rootLogger = logging.getLogger()
rootLogger.setLevel(logging.DEBUG)  # This is not the log level of stream handler
del logging, rootLogger


# Version Definition
from importlib.metadata import version  # noqa: E402

try:
    __version__ = version("neclib")
except:  # noqa: E722
    __version__ = "0.0.0"  # Fallback.
del version


# Import global functions
import sys  # noqa: E402

from .core import get_logger  # noqa: F401, E402
from .core import config, configure  # noqa: F401, E402
from .core.data_type import *  # noqa: F401, E402, F403
from .core.exceptions import *  # noqa: F401, E402, F403

# Warn Restriction Imposed by Environment
if sys.platform != "linux":
    logger = get_logger("neclib")
    logger.warning(
        "Device drivers for Interface PCI boards are only supported on Linux."
    )
del sys  # get_logger is intentionally kept in the namespace.

# Subpackages
from . import controllers  # noqa: F401, E402
from . import core  # noqa: F401, E402
from . import recorders  # noqa: F401, E402
from . import safety  # noqa: F401, E402
from . import simulators  # noqa: F401, E402
from . import utils  # noqa: F401, E402

# Wait for all background tasks to complete.
concurrent.futures.wait(futures, timeout=None)
executor.shutdown()
del _TimeConsumingTasks, concurrent, executor, futures
