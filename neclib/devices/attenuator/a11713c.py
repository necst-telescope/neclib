import astropy.units as u
import ogameasure

from ... import get_logger
from ...core.security import busy
from ...utils import skip_on_simulator
from .attenuator_base import NetworkAttenuator


class A11713C(NetworkAttenuator):
    """Attenuator, which can attennuate four IF sigal power.

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

    model: str
        Attenuator model which you use in this device.
        Following model are available:
        "NA", "AG8494g", "AG8494h", "AG8495g", "AG8495h", "AG8495k",
        "AG8496g", "AG8496h", "AG8497k", "AG84904k", "AG84904l",
        "AG84904m", "AG84905m", "AG84906k", "AG84906l", "AG84907k",
        "AG84907l", "AG84908m"
        For example:
        `{ 1LU = "AG8494g", 1LL = "AG8495k", 1RU = "AG84905m", 1RL = "AG84907k"}`

    channel : Dict[str]
        Human-readable channel name. The value should be
        mapping from human readableversion (str) to
        device level identifier (int). You can assign any name to the
        channels up to four channels: "1X" (BANK1, X), "1Y" (BANK1, Y),
        "2X" (BANK2, X), "2Y" (BANK2 Y).
        For example: `{ 1LU = "1X", 1LL = "1Y", 1RU = "2X", 1RL = "2Y"}`

    """

    Manufacturer = "Agilent"
    Model = "11713C"

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
        self.io = ogameasure.Agilent.agilent_11713C(com)
        self.model_check()
        pass

    def model_check(self) -> None:
        for id in self.Config.model.keys():
            bank = int(self.Config.channel[id][0])
            ch = self.Config.channel[id][1]
            model = self.Config.model[id]
            dev_model = self.io.att_model_query(ch, bank)
            if model != "AG8495k":
                _model = model[:-1]
            else:
                _model = model[:-1] + model[-1].upper()
            if _model != dev_model:
                raise ValueError(
                    "Attenutor model in config is not match with"
                    f"the model which you set in device. {id}: {bank}, {ch}, {model}"
                )
            pass

    def get_loss(self, id: str) -> u.Quantity:
        with busy(self, "busy"):
            bank = int(self.Config.channel[id][0])
            ch = self.Config.channel[id][1]
            try:
                return self.io.att_level_query(ch, bank) * u.dB
            except IndexError:
                pass
            raise ValueError(f"Invalid channel: {ch}")

    def set_loss(self, dB: int, id: str) -> None:
        with busy(self, "busy"):
            bank = int(self.Config.channel[id][0])
            ch = self.Config.channel[id][1]
            self.io.att_level_set(dB, ch, bank)

    def finalize(self) -> None:
        self.io.com.close()

    def close(self) -> None:
        self.finalize()
