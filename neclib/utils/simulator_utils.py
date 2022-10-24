__all__ = ["skip_on_simulator"]

import functools


def skip_on_simulator(func):
    from .. import config  # Avoid circular import

    @functools.wraps(func)
    def _skip_if_simulator(*args, **kwargs):
        if config.simulator:
            return None
        return func(*args, **kwargs)

    return _skip_if_simulator
