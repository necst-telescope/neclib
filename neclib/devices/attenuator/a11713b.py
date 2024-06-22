import astropy.units as u
import ogameasure

from ...core.security import busy
from ...utils import skip_on_simulator
from .attenuator_base import NetworkAttenuator


class A11713B(NetworkAttenuator):
    """Attenuator, which can attennuate IF sigal power.

    Notes
    -----

    Configuration items for this device:

    host : str
        IP address for GPIB communicator.

    port : int
        GPIB port of using devices.

    channel : Dict[str]
        Human-readable channel name. The value should be
        mapping from human readableversion (str) to
        device level identifier (int). You can assign any name to the
        channels up to two channels: "X", "Y".
        For example: `{ 2R = X, 2L = Y}`

    """

    Manufacturer = "Agilent"
    Model = "11713B"

    Identifier = "host"

    @skip_on_simulator
    def __init__(self) -> None:
        com = ogameasure.gpib_prologix(host=self.Config.host, gpibport=self.Config.port)
        self.io = ogameasure.Agilent.agilent_11713B(com)

    def get_loss(self, id: str) -> u.Quantity:
        with busy(self, "busy"):
            ch = self.Config.channel[id]
            try:
                return self.io.att_level_query(ch) * u.dB
            except IndexError:
                pass
            raise ValueError(f"Invalid channel: {ch}")

    def set_loss(self, dB: int, id: str) -> None:
        with busy(self, "busy"):
            ch = self.Config.channel[id]
            self.io.att_level_set(dB, ch)

    def finalize(self) -> None:
        self.io.com.close()
