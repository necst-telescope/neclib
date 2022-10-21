from collections import defaultdict
from functools import partial
from types import SimpleNamespace
from typing import Dict, List


class Status:
    """Status manager.

    Parameters
    ----------
    levels
        List of level names, default is ["warning", "critical"]. The names should be
        given in ascending order in severity.

    Raises
    ------
    ValueError
        If (at least) one of level names are reserved by Python.

    Examples
    --------
    >>> status = Status()
    >>> status["topic1"].warning = True
    >>> status["topic1"]
    namespace(warning=True, critical=False)
    >>> status["topic2"] = {"warning": False, "critical": False}
    >>> status.warning()
    True
    >>> status.critical()
    False

    """

    def __init__(self, levels: List[str] = ["warning", "critical"]) -> None:
        # Check if levels are assignable
        reserved_attr = [
            level for level in levels if hasattr(self, level) or level.startswith("__")
        ]
        if len(reserved_attr) > 0:
            raise ValueError(f"Level names {reserved_attr} not assignable")

        self.__status: Dict[str, SimpleNamespace] = defaultdict(
            lambda: SimpleNamespace(**{k: None for k in levels})
        )
        self.__levels = levels

        # Assign property-like checkers
        for level in levels:
            setattr(self, level, partial(self.__get_status, level))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(severity: {' < '.join(self.__levels)})"

    def __get_status(self, level: str) -> bool:
        """Check if any topic has set to the level."""
        if any([getattr(v, level) for v in self.__status.values()]):
            return True  # If any topic is in this exact level, return True

        next_level_idx = self.__levels.index(level) + 1
        if next_level_idx == len(self.__levels):
            return False  # No truthy value found even in severer levels
        return self.__get_status(self.__levels[next_level_idx])  # Check severer levels

    def __getitem__(self, key):
        return self.__status[key]

    def __setitem__(self, key, value):
        if not isinstance(value, dict):
            raise TypeError("Value must be dict")
        value = {k: v for k, v in value.items() if k in self.__status[key].__dict__}
        self.__status[key].__dict__.update(value)
