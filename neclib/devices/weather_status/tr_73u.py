__all__ = ["TR_73U"]

from typing import Literal

import astropy.units as u
from ... import config
from .weather_base import Weather

class TR_73U(Weather):

    Manufacturer = ""
    Model = "TR_73U"

    def __init__(self) -> None:
        ...
    
    def read(self) -> Float64:
        while not rospy.is_shutdown():
            data = self.ondotori.output_current_data()
            try:
                d = struct.unpack('26B', data)
                temp = (d[6]*16**2+d[5]-1000)/10
                humid = (d[8]*16**2+d[7]-1000)/10
                press = (d[10]*16**2+d[9])/10
            except:
                pass
            time.sleep(5)
        pass

        self.temperature = 
        self.fumidity = 
        self.pressure = 


    def finalize(self) -> None:
        pass