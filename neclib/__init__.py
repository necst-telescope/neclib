# flake8: noqa

try:
    from importlib.metadata import version  # Python 3.8+
except ImportError:
    from importlib_metadata import version

try:
    __version__ = version("neclib")
except:
    __version__ = "0.0.0"  # Fallback.

# Aliases
from .device_control import *
from .exceptions import *

# Submodules
from . import units

# Subpackages
from . import parameters
from . import simulator
from . import utils
