import time

import astropy.units as u
import ogameasure

from ... import get_logger
from ...core.security import busy
from .thermometer_base import Thermometer


class Model218(Thermometer):

    Manufacturer = "LakeShore"
    Model = "Model218"

    Identifier = "communicator"

    def __init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__)

        if self.Config.communicator == "GPIB":
            com = ogameasure.gpib_prologix(
                host=self.Config.host, gpibport=self.Config.port
            )
            self.thermometer = ogameasure.Lakeshore.model218(com)
        elif self.Config.communicator == "USB":
            self.thermometer = ogameasure.Lakeshore.model218_usb(self.Config.usb_port)
        else:
            self.logger.warning(
                f"There is not exsited communicator: {self.Config.communicator}."
                "Please choose USB or GPIB."
            )

    def get_temp(self, id: str) -> u.Quantity:
        ch = self.Config.channel[id]
        with busy(self, "busy"):
            data = self.thermometer.kelvin_reading_query(ch)
            time.sleep(0.1)
            return data * u.K

    def finalize(self) -> None:
        self.thermometer.com.close()
