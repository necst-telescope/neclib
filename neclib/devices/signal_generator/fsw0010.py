import astropy.units as u
import time
import ogameasure
from ... import config
from .signal_generator_base import SignalGenerator
from ...utils import busy
from ...units import dBm


class FSW0010(SignalGenerator):

    Manufacturer: str = "PhaseMatrix"
    Model = "FSW0010"

    def __init__(self):
        com = ogameasure.ethernet(config.rx_fsw0010_host, config.rx_fsw0010_port)
        self.sg = ogameasure.Phasematrix.FSW0010(com)
        self.sg.use_external_reference_source()

    def set_freq(self, freq_GHz):
        with busy(self, "busy"):
            self.sg.freq_set(freq_GHz)
            time.sleep(1)
            return

    def set_power(self, power_dBm):
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
