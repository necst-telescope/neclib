"""Utility functions for data structure handling."""

__all__ = ["update_list"]

from typing import Any, List


def update_list(param: List[Any], new_value: Any) -> None:
    """Drop old value and assign new one, preserving list length.

    Parameters
    ----------
    param
        Data buffer.
    new_value
        Value to be assigned into ``param``.

    Examples
    --------
    >>> param = [0, 1]
    >>> update_list(param, 3)
    >>> param
    [1, 3]

    """
    if isinstance(param, list):
        param.pop(0)
        param.append(new_value)
    else:
        raise TypeError(f"``{type(param)}`` isn't supported, use ``list`` instead.")
