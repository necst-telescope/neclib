# flake8: noqa

try:
    from importlib_metadata import version
except ImportError:
    from importlib.metadata import version  # Python 3.8+

try:
    __version__ = version("neclib")
except:
    __version__ = "0.0.0"  # Fallback.

# Aliases
from .device_control import *

# Subpackages
from . import simulator
