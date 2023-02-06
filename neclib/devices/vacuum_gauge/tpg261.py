import astropy.units as u
import ogameasure

from ...core import logic
from .vacuum_gauge_base import VacuumGauge


class TPG261(VacuumGauge):

    Model = "TPG261"
    Manufacturer = "Pfeiffer"

    Identifier = "host"

    def __init__(self, **kwargs):
        com = ogameasure.ethernet(self.Config.host, self.Config.port)
        self.io = ogameasure.Pfeiffer.tpg261_lan(com)
        self.io.pres_unit_pa()

    def get_pressure(self) -> u.Quantity:
        with logic.busy(self, "busy"):
            return self.io.pressure() * u.Pa

    def finalize(self):
        self.io.com.close()
