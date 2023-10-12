__all__ = ["VantagePro2"]

import struct
from weather import units
from weather.stations import davis as weatherlink

import time

import astropy.units as u

from.weather_station_base import WeatherStation



class VantagePro2(WeatherStation):
    Manufacturer = "Davis"
    Model = "VantagePro2"
    
    self.device = '/dev/tty.usbserial-0001'

    def __init__(self) -> None:
        self.vantage = weatherlink.VantagePro(self.device)


    def _get_data(self) -> dict:
    
        ret = self.vantage.parse()
            
        if ret["EOL"] == b'\n\r':
            return ret
                
        else:
            print("Can not access weather station")
    
    def get_out_temp(self) -> u.Quantitiy :
        data = self._get_data()
        data_K = (units.fahrenheit_to_kelvin(data["TempOut"])*u.K)
        return data_K
    
    def get_in_temp(self) -> u.Quantitiy :
        data = self._get_data()
        data_K = (units.fahrenheit_to_kelvin(data["TempIn"])*u.K)
        return data_K

    def get_out_hum(self) -> float :
        data =  self._get_data()
        return data["HumOut"] * 0.01
    
     def get_in_hum(self) -> float :
        data =  self._get_data()
        return data["HumIn"] * 0.01

    def get_press(self) -> u.Quantity :
        data = self._get_data()
        data_press = units.incConv_to_Pa(ret["Pressure"])*10* u.hPa
        return data_press

    def get_wind_speed(self) -> u.Quantity :
        data = self._get_data()
        data_WindSpeed = units.mph_to_m_sec(ret["WindSpeed"]) *u.m/u.second
        return data_WindSpeed

    def get_wind_dir(self) -> u.Quantity :
        data = self._get_data()
        return ret["WindDir"]*u.deg

    def get_rainrate(self) -> float:
        data = self._get_data()
        return ret["RainRate"]

    def finalize(self) -> None:
        self.vantage.__del__()
