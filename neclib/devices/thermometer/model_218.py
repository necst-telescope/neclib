import time

import astropy.units as u
import ogameasure

from ...core.security import busy
from .thermometer_base import Thermometer


class Model218(Thermometer):

    Manufacturer = "LakeShore"
    Model = "Model218"

    Identifier = "usb_port"

    def __init__(self) -> None:
        self.thermometer = ogameasure.Lakeshore.model218_usb(self.Config.usb_port)

    def get_temp(self, id: str) -> u.Quantity:
        ch = self.Config.channel[id]
        with busy(self, "busy"):
            data = self.thermometer.kelvin_reading_query(ch)
            time.sleep(0.1)
            return data * u.K

    def finalize(self) -> None:
        self.thermometer.com.close()
