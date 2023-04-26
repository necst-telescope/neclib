"""Pure Python tools for NECST."""


# Perform time-consuming downloads
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
# Set minimum log level; not just for stream handler but for any handler attached.
# Stream handler will selectively handle logs of INFO or higher levels, but DEBUG level
# ones are not something you can completely ignore (may be recorded into log file)
rootLogger.setLevel(logging.DEBUG)
del logging, rootLogger


# Project version
from importlib.metadata import version  # noqa: E402

__version__ = version("neclib")
del version


# Subpackages
# `devices` isn't included, since they can be OS-dependent hence verbose warnings
from . import controllers  # noqa: F401, E402
from . import coordinates  # noqa: F401, E402
from . import core  # noqa: F401, E402
from . import recorders  # noqa: F401, E402
from . import safety  # noqa: F401, E402
from . import simulators  # noqa: F401, E402
from . import utils  # noqa: F401, E402

# Aliases
from .core import config, configure, get_logger  # noqa: F401, E402
from .core.data_type import *  # noqa: F401, E402, F403
from .core.exceptions import *  # noqa: F401, E402, F403

# Wait for all background tasks to complete. Timeout should be sufficiently large,
# otherwise attempt to download data files will be made every time importing `neclib`,
# until it completes in restricted duration.
concurrent.futures.wait(futures, timeout=None)
executor.shutdown()
del _TimeConsumingTasks, concurrent, executor, futures
