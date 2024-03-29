import time

import astropy.units as u
import ogameasure

from ...core.security import busy
from .thermometer_base import Thermometer


class Model218(Thermometer):
    """Thermometer, which can check tempareture of cryostat.

    Notes
    -----
    If you use this device with GPIB, you should write "Model218" in `config.toml`

    Configuration items for this device:

    host : str
        IP address for GPIB communicator.

    port : int
        GPIB port of using devices. Please check device setting.

    """

    Manufacturer = "LakeShore"
    Model = "Model218"

    Identifier = "host"

    def __init__(self) -> None:
        com = ogameasure.gpib_prologix(host=self.Config.host, gpibport=self.Config.port)
        self.thermometer = ogameasure.Lakeshore.model218(com)

    def get_temp(self, id: str) -> u.Quantity:
        ch = self.Config.channel[id]
        with busy(self, "busy"):
            data = self.thermometer.kelvin_reading_query(ch)
            time.sleep(0.1)
            return data * u.K

    def finalize(self) -> None:
        self.thermometer.com.close()
