from abc import abstractmethod

import astropy.units as u

from ..device_base import DeviceBase


class WeatherStation(DeviceBase):

    Manufacturer: str = ""
    Model: str

    
    @abstractmethod
    def get_temperature(self) -> u.Quantity:
        ...

    @abstractmethod
    def get_humidity(self) -> float:
        ...
        
    @abstractmethod
    def get_pressure(self) -> u.Quantity:
        ...
    
    @abstractmethod
    def get_in_temperature(self) -> u.Quantity:
        ...

    @abstractmethod
    def get_in_humidity(self) -> float :
        ...
    
    @abstractmethod
    def get_wind_speed(self) -> u.Quantity:
        ...

    @abstractmethod
    def get_wind_direction(self) -> u.Quantity:
        ...

    @abstractmethod
    def get_rain_rate(self) -> float:
        ...

    @abstractmethod
    def finalize(self) -> None:
        ...

