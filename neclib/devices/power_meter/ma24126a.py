import astropy.units as u
import ogameasure

from ... import get_logger, utils
from .power_meter_base import PowerMeter


class MA24126A(PowerMeter):

    Model = "MA24126A"
    Manufacturer = "Anritsu"

    Identifier = "port"

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.io = ogameasure.Anritsu.ma24126a(self.Config.port)
        self.io.start()

    def get_power(self) -> u.Quantity:
        with utils.busy(self, "busy"):
            ret = self.io.power()
            power = float(ret.decode().split("\n")[0])
            return power * u.mW

    def zero_set(self) -> None:
        with utils.busy(self, "busy"):
            self.logger.info("##### usb power meter is doing zero setting now ####")
            self.io.zero_set()
            self.logger.info("##### usb power meter finished zero setting  ####")

    def finalize(self):
        self.io.close()
