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

    communicator : str
    Communicator of thermometer. LAN or RS232 can be chosen.

    host : str
        IP address for ethernet communicator.
        If you use LAN communicator, you must set this parameter.

    port : int
        ethernet port of using devices. Please check device setting.
        If you use LAN communicator, you must set this parameter.

    rs232_port : str
        RS232 port of using devices.
        If you use RS232 communicator, you must set this parameter.

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
            com = ogameasure.serial(self.Config.rs232_port)
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
            elif self.Config.communicator == "RS232":
                res = self.io.read_single_pressure()
                return res["value"] * u.torr

    def finalize(self):
        self.io.com.close()
