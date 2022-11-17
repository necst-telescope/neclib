"""Modules necessary to run simulator.

Notes
-----
NECST modules should support simulator mode. Here is a collection of modules necessary
to implement the mode.

Important
---------
If there's a corresponding non-simulator script, functionalities in the original one
should be used as much as possible, through inheriting and overriding, to ensure the
behavior is the same as real one.

"""

from .antenna import *  # noqa: F401, F403
