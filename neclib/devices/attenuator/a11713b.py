import astropy.units as u
import ogameasure

from ... import get_logger
from ...core.security import busy
from ...utils import skip_on_simulator
from .attenuator_base import NetworkAttenuator


class A11713B(NetworkAttenuator):
    """Attenuator, which can attennuate IF sigal power.

    Notes
    -----

    Configuration items for this device:

    communicator : str
        Communicator of thermometer. GPIB or LAN can be chosen.

    host : str
        IP address for GPIB and ethernet communicator.

    gpib_port : int
        GPIB port of using devices. Please check device setting.
        If you use GPIB communicator, you must set this parameter.

    lan_port : int
        LAN port of using devices. This parameter is setted to 5025 by manufacturer.
        If you use LAN communicator, you must set this parameter.

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
        self.logger = get_logger(self.__class__.__name__)

        if self.Config.communicator == "GPIB":
            com = ogameasure.gpib_prologix(self.Config.host, self.Config.gpib_port)
        elif self.Config.communicator == "LAN":
            com = ogameasure.ethernet(self.Config.host, self.Config.lan_port)
        else:
            self.logger.warning(
                f"There is not exsited communicator: {self.Config.communicator}."
                "Please choose USB or GPIB."
            )
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
