import astropy.units as u
import ogameasure

from ... import get_logger
from ...core.security import busy
from .vacuum_gauge_base import VacuumGauge


class TPG261(VacuumGauge):
    """Vacuum Gauge, which can check preassure of cryostat.

    Notes
    -----

    Configuration items for this device:

    host : str
        IP address for ethernet communicator.

    port : int
        ethernet port of using devices.

    """

    Model = "TPG261"
    Manufacturer = "Pfeiffer"

    Identifier = "communicator"

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

        if self.Config.communicator == "LAN":
            com = ogameasure.ethernet(self.Config.host, self.Config.port)
            self.io = ogameasure.Pfeiffer.tpg261_lan(com)
            self.io.pres_unit_torr()

        elif self.Config.communicator == "RS232":
            com = ogameasure.serial(self.Config.host, self.Config.port)
            self.io = ogameasure.Pfeiffer.tpg261(com)
            self.io.unit_command(unit=1)

        else:
            self.logger.warning(
                f"There is not exsited communicator: {self.Config.communicator}."
                "Please choose RS232 or LAN."
            )

    def get_pressure(self) -> u.Quantity:
        with busy(self, "busy"):
            if self.Config.communicator == "LAN":
                return self.io.pressure() * u.torr
            elif self.Config.communicator == "RS232C":
                return self.io.read_pressure() * u.torr

    def finalize(self):
        self.io.com.close()
