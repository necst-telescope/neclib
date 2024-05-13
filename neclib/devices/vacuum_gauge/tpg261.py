import astropy.units as u
import ogameasure

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

    Identifier = "host"

    def __init__(self):
        com = ogameasure.ethernet(self.Config.host, self.Config.port)
        self.io = ogameasure.Pfeiffer.tpg261_lan(com)
        self.io.pres_unit_pa()

    def get_pressure(self) -> u.Quantity:
        with busy(self, "busy"):
            return self.io.pressure() * u.Pa

    def finalize(self):
        self.io.com.close()
