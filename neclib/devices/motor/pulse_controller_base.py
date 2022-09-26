from typing import Literal

from abc import ABC, abstractmethod


class PulseController(ABC):

    Manufacturer: str = ""
    Model: str

    @abstractmethod
    def set_step(self, step: int, axis: Literal["az", "el"]) -> None:
        ...

    @abstractmethod
    def set_speed(self, speed: float, axis: Literal["az", "el"]) -> None:
        ...

    @abstractmethod
    def get_step(self, axis: Literal["az", "el"]) -> int:
        ...

    @abstractmethod
    def get_speed(self, axis: Literal["az", "el"]) -> float:
        ...

    @abstractmethod
    def finalize(self) -> None:
        ...
