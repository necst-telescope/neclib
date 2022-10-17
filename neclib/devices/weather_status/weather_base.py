from abc import ABC, abstractmethod
from typing import Literal
from std_msgs.msg import Float64

class Weather(ABC):

    Manufacturer: str = ""
    Model: str

    @abstractmethod
    def read(self, parameters: Literal["temperature", "humidity", "pressure"]) -> Float64:
        ...
    
    @abstractmethod
    def finalize(self) -> None:
        ...
