__all__ = ["clip", "frange"]

from typing import Generator


def clip(value: float, minimum: float, maximum: float) -> float:
    """Limit the ``value`` to the range [``minimum``, ``maximum``]."""
    return min(max(minimum, value), maximum)


def frange(start: float, stop: float, step: float = 1) -> Generator[float, None, None]:
    """Flexible range."""
    value = start
    while value < stop:
        yield value
        value += step
