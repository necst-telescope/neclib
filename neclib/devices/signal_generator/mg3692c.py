import time
from typing import Optional, Union

import astropy.units as u
import ogameasure

from ...core.security import busy
from ...core.units import dBm
from ...utils import skip_on_simulator
from .signal_generator_base import SignalGenerator


class MG3692C(SignalGenerator):
    """Signal Generator, which can supply Local Signal.

    Notes
    -----

    Configuration items for this device:

    host : str
        IP address for ethernet communicator.

    port : int
        ethernet port of using devices.

    """

    Manufacturer: str = "Anritsu"
    Model = "MG3692C"

    Identifier = "host"

    @skip_on_simulator
    def __init__(self) -> None:
        com = ogameasure.gpib_prologix(host=self.Config.host, gpibport=self.Config.port)
        self.sg = ogameasure.Anritsu.mg3692c(com)

    def set_freq(self, GHz: Union[int, float]) -> None:
        with busy(self, "busy"):
            self.sg.freq_set(GHz)
            time.sleep(0.1)
        return

    def set_power(self, dBm: Union[int, float]) -> None:
        with busy(self, "busy"):
            self.sg.power_set(dBm)
            time.sleep(0.1)
        return

    def get_freq(self) -> u.Quantity:
        with busy(self, "busy"):
            f = self.sg.freq_query()
            time.sleep(0.1)
            return f * u.Hz

    def get_power(self) -> u.Quantity:
        with busy(self, "busy"):
            f = self.sg.power_query()
            time.sleep(0.1)
            return f * dBm

    def start_output(self) -> None:
        with busy(self, "busy"):
            self.sg.output_on()
            time.sleep(0.1)
        return

    def stop_output(self) -> None:
        with busy(self, "busy"):
            self.sg.output_off()
            time.sleep(0.1)
        return

    def get_output_status(self) -> Optional[bool]:
        with busy(self, "busy"):
            f = self.sg.output_query()
            time.sleep(0.1)
            if f == 1:
                return True
            elif f == 0:
                return False
            else:
                return None

    def finalize(self) -> None:
        self.stop_output()
        self.sg.close()
        return

    def close(self) -> None:
        self.sg.close()
        return
