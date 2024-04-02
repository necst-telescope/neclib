import astropy.units as u
import ogameasure

from ... import get_logger
from ...core.security import busy
from .power_meter_base import PowerMeter


class ML2437A(PowerMeter):
    # configに以下を追加すること
    # [powermeter.calib]
    # _ = "ML2437A"
    # host = "192.168.100.106"
    # port = 1234

    Model = "ML2437A"
    Manufacturer = "Anritsu"

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

        host = self.Config.host
        gpibport = self.Config.port
        com = ogameasure.gpib_prologix(host, gpibport)
        self.pm = ogameasure.Anritsu.ml2437a(com)

    def get_power(self, ch) -> u.Quantity:
        with busy(self, "busy"):
            power = self.pm.measure(ch)
            return power * u.mW
