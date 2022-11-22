import time

import astropy.units as u
import ogameasure

from ...units import dBm
from ...utils import busy, skip_on_simulator
from .signal_generator_base import SignalGenerator


class FSW0020(SignalGenerator):

    Manufacturer: str = "PhaseMatrix"
    Model = "FSW0020"

    Identifier = "host"

    @skip_on_simulator
    def __init__(self):
        com = ogameasure.ethernet(self.Config.host, self.Config.port)
        self.sg = ogameasure.Phasematrix.FSW0020(com)
        self.sg.use_external_reference_source()

    def set_freq(self, freq_GHz):
        with busy(self, "busy"):
            self.sg.freq_set(freq_GHz)
            time.sleep(1)
            return

    def set_power(self, power_dBm):
        """Set the power of the signal generator output.

        Attention
        ---------
        The ability to change power of this signal generator is optional configuration.
        For products without the option, this function has no effect but raises no
        error.

        """
        with busy(self, "busy"):
            self.sg.power_set(power_dBm)
            time.sleep(1)
            return

    def get_freq(self):
        with busy(self, "busy"):
            f = self.sg.freq_query()
            time.sleep(1)
            return f * u.Hz

    def get_power(self):
        """Get the power of the signal generator output.

        Attention
        ---------
        The ability to change power of this signal generator is optional configuration.
        For products without the option, this function may return meaningless value.

        """
        with busy(self, "busy"):
            f = self.sg.power_query()
            time.sleep(1)
            return f * dBm

    def start_output(self):
        with busy(self, "busy"):
            self.sg.output_on()
            time.sleep(1)
            return

    def stop_output(self):
        with busy(self, "busy"):
            self.sg.output_off()
            time.sleep(1)
            return

    def get_output_status(self):
        with busy(self, "busy"):
            f = self.sg.output_query()
            time.sleep(1)
            if f == 1:
                return True
            elif f == 0:
                return False
            else:
                return None

    def finalize(self):
        self.stop_output()
        try:
            self.sg.com.close()
        except AttributeError:
            pass
