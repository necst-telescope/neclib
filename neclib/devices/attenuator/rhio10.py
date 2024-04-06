import astropy.units as u
import ogameasure

from ... import utils
from ...core.security import busy
from .attenuator_base import Attenuator


class RHIO10(Attenuator):
    """Attenuator, which can attennuate IF sigal power.

    Notes
    -----

    Configuration items for this device:

    host : str
        IP address for ethernet communicator.

    port : int
        ethernet port of using devices.

    channel : Dict[str, int]
        Human-readable channel name. The value should be
        mapping from human readableversion (str) to
        device level identifier (int). You can assign any name to the
        channels up to two channels. For example: `{ CH1 = 1, CH2 = 2}`

    """

    Manufacturer: str = "SENA"
    Model: str = "RHIO10"

    Identifier = "host"

    @utils.skip_on_simulator
    def __init__(self) -> None:
        com = ogameasure.ethernet(self.Config.host, self.Config.port)
        self.io = ogameasure.SENA.adios(com)

    def get_loss(self, id: str) -> u.Quantity:
        with busy(self, "busy"):
            ch = self.Config.channel[id]
            try:
                if ch == 1:
                    return self.io.get_att1() << u.dB
                elif ch == 2:
                    return self.io.get_att2() << u.dB
            except IndexError:
                pass
            raise ValueError(f"Invalid channel: {ch}")

    def set_loss(self, dB: int, id: str) -> None:
        with busy(self, "busy"):
            ch = self.Config.channel[id]
            self.io._set_att(ch, int(dB))

    def finalize(self) -> None:
        self.io.com.close()
