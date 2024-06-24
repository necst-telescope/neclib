import time
from typing import Optional, Union

import astropy.units as u
import ogameasure

from ... import get_logger
from ...core.security import busy
from ...core.units import dBm
from ...utils import skip_on_simulator
from .signal_generator_base import SignalGenerator


class E8257D(SignalGenerator):
    """Signal Generator, which can supply Local Signal.

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

    """

    Manufacturer: str = "Agilent"
    Model = "E8257D"

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
        self.sg = ogameasure.Agilent.E8257D(com)

    def set_freq(self, freq_GHz: Union[int, float]) -> None:
        with busy(self, "busy"):
            self.sg.freq_set(freq_GHz)
            time.sleep(1)
            return

    def set_power(self, power_dBm: Union[int, float]) -> None:
        with busy(self, "busy"):
            self.sg.power_set(power_dBm)
            time.sleep(1)
            return

    def get_freq(self) -> u.Quantity:
        with busy(self, "busy"):
            f = self.sg.freq_query()
            time.sleep(1)
            return f * u.Hz

    def get_power(self) -> u.Quantity:
        with busy(self, "busy"):
            f = self.sg.power_query()
            time.sleep(1)
            return f * dBm

    def start_output(self) -> None:
        with busy(self, "busy"):
            self.sg.output_on()
            time.sleep(1)
            return

    def stop_output(self) -> None:
        with busy(self, "busy"):
            self.sg.output_off()
            time.sleep(1)
            return

    def get_output_status(self) -> Optional[bool]:
        with busy(self, "busy"):
            f = self.sg.output_query()
            time.sleep(1)
            if f == 1:
                return True
            elif f == 0:
                return False
            else:
                return None

    def finalize(self) -> None:
        self.stop_output()
        self.sg.com.close()
