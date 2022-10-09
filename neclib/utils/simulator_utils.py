__all__ = ["skip_on_simulator"]

import functools

from .. import config


def skip_on_simulator(func):
    @functools.wraps(func)
    def _skip_if_simulator(*args, **kwargs):
        if config.simulator:
            return None
        return func(*args, **kwargs)

    return _skip_if_simulator
