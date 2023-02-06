from functools import wraps


def disabled(func):
    """A decorator to disable a function or method.

    This may be used to make a tentative implementation not accessible.

    """

    @wraps(func)
    def _disabled(*args, **kwargs):
        raise NotImplementedError

    return _disabled
