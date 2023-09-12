from abc import abstractmethod

import astropy.units as u

from ..device_base import DeviceBase


class WeatherStation(DeviceBase):

    Manufacturer: str = ""
    Model: str

    @abstractmethod
    def get_InTemp(self) -> u.Quantity:
        ...
    
    @abstractmethod
    def get_OutTemp(self) -> u.Quantity:
        ...

    @abstractmethod
    def get_InHum(self) -> float:
        ...
    
    @abstractmethod
    def get_OutHum(self) -> float:
        ...
        
    @abstractmethod
    def get_press(self) -> u.Quantity:
        ...
    
    @abstractmethod
    def get_WindSpeed(self) -> float:
        ...

    @abstructmethod
    def get_WindDirection(self) -> float:
        ...
    
    @abstractmethod
    def get_RainRate(self) -> float:
        ...

    @abstractmethod
    def finalize(self) -> None:
        ...

