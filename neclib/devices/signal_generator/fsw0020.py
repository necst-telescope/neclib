import time
import ogameasure
from ... import config
from .signal_generator_base import SignalGenerator


class fsw0010(SignalGenerator):

    Manufacturer: str = "Phasematrix"
    Model = "fsw0020"

    def __init__(self):
        self.communicating = True
        com = ogameasure.ethernet(config.rx_fsw0020_host, config.rx_fsw0020_port)
        self.sg = ogameasure.Phasematrix.FSW0010(com)
        self.sg.use_external_reference_source()

    def set_freq(self, freq_GHz):
        if self.communicating is False:
            self.sg.freq_set(freq_GHz)
            time.sleep(1)
            self.communicating = True
            return
        elif self.communicating is True:
            self.communicating = False
            self.sg.freq_set(freq_GHz)
            time.sleep(1)
            self.communicating = True
            return

    def set_power(self, power_dBm):
        if self.communicating is False:
            self.sg.power_set(power_dBm)
            time.sleep(1)
            self.communicating = True
            return
        elif self.communicating is True:
            self.communicating = False
            self.sg.power_set(power_dBm)
            time.sleep(1)
            self.communicating = True
            return

    def set_onoff(self, onoff):
        if self.communicating is False:
            self.sg.output_set(onoff)
            time.sleep(1)
            self.communicating = True
            return
        elif self.communicating is True:
            self.communicating = False
            self.sg.output_set(onoff)
            time.sleep(1)
            self.communicating = True
            return

    def get_freq(self):
        if self.communicating is False:
            self.sg.freq_query()
            time.sleep(1)
            self.communicating = True
            return
        elif self.communicating is True:
            self.communicating = False
            self.sg.freq_query()
            time.sleep(1)
            self.communicating = True
            return

    def get_power(self):
        if self.communicating is False:
            self.sg.power_query()
            time.sleep(1)
            self.communicating = True
            return
        elif self.communicating is True:
            self.communicating = False
            self.sg.power_query()
            time.sleep(1)
            self.communicating = True
            return
