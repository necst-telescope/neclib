__all__ = ["update_list"]

from typing import Any, List


def update_list(param: List[Any], new_value: Any) -> None:
    """Drop old parameter and assign new one, preserving array length."""
    param.pop(0)
    param.append(new_value)
