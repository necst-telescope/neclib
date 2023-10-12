from abc import abstractmethod

import astropy.units as u

from ..device_base import DeviceBase


class WeatherStation(DeviceBase):

    Manufacturer: str = ""
    Model: str

    @abstractmethod
    def get_in_temp(self) -> u.Quantity:
        ...
    
    @abstractmethod
    def get_out_temp(self) -> u.Quantity:
        ...

    @abstractmethod
    def get_in_hum(self) -> float:
        ...
    
    @abstractmethod
    def get_out_hum(self) -> float:
        ...
        
    @abstractmethod
    def get_press(self) -> u.Quantity:
        ...
    
    @abstractmethod
    def get_wind_speed(self) -> u.Quantity:
        ...

    @abstructmethod
    def get_wind_dir(self) -> u.Quantity:
        ...
    
    @abstractmethod
    def get_rain_rate(self) -> float:
        ...

    @abstractmethod
    def finalize(self) -> None:
        ...

