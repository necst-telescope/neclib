from typing import Any, Dict, Tuple

from .path_base import Path


class Linear(Path):

    tight = True
    infinite = False
    waypoint = False

    @property
    def arguments(self) -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        ...


class Accelerate(Path):

    tight = False
    infinite = False
    waypoint = False

    @property
    def arguments(self) -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        ...


class Standby(Path):

    tight = True
    infinite = True
    waypoint = True

    @property
    def arguments(self) -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        ...
