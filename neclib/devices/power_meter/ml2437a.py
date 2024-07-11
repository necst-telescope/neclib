import ogameasure

from ... import get_logger
from ...core.security import busy
from ...core.units import dBm
from .power_meter_base import PowerMeter


class ML2437A(PowerMeter):
    """PowerMeter, which can measure IF signal power.

    Notes
    -----

    Configuration items for this device:

    host : str
        IP address for GPIB communicator.

    port : int
        GPIB port of using devices. Please check device setting.

    """

    Model = "ML2437A"
    Manufacturer = "Anritsu"

    Identifier = "host"

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

        host = self.Config.host
        gpibport = self.Config.port
        com = ogameasure.gpib_prologix(host, gpibport)
        self.pm = ogameasure.Anritsu.ml2437a(com)

    def get_power(self) -> dBm:
        with busy(self, "busy"):
            power = self.pm.measure()
            return power * dBm

    def finalize(self) -> None:
        self.pm.com.close()
        return
