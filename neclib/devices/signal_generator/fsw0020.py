import time
import ogameasure
from ... import config
from .signal_generator_base import SignalGenerator


class FSW0020(SignalGenerator):

    Manufacturer: str = "PhaseMatrix"
    Model = "FSW0020"

    def __init__(self):
        self.communicating = True
        com = ogameasure.ethernet(config.rx_fsw0020_host, config.rx_fsw0020_port)
        self.sg = ogameasure.Phasematrix.FSW0020(com)
        self.sg.use_external_reference_source()

    def set_freq(self, freq_GHz):
        while self.busy is True:
            time.sleep(1)
        else:
            self.busy = True
            self.sg.freq_set(freq_GHz)
            time.sleep(1)
            self.busy = False
            return

    def set_power(self, power_dBm):
        while self.busy is True:
            time.sleep(1)
        else:
            self.busy = True
            self.sg.power_set(power_dBm)
            time.sleep(1)
            self.busy = False
            return

    def get_freq(self):
        while self.busy is True:
            time.sleep(1)
        else:
            self.busy = True
            self.sg.freq_query()
            time.sleep(1)
            self.busy = False
            return

    def get_power(self):
        while self.busy is True:
            time.sleep(1)
        else:
            self.busy = True
            self.sg.power_query()
            time.sleep(1)
            self.busy = False
            return

    def start_output(self):
        while self.busy is True:
            time.sleep(1)
        else:
            self.busy = True
            self.sg.output_on()
            time.sleep(1)
            self.busy = False
            return

    def stop_output(self):
        while self.busy is True:
            time.sleep(1)
        else:
            self.busy = True
            self.sg.output_off()
            time.sleep(1)
            self.busy = False
            return

    def get_output_status(self):
        while self.busy is True:
            time.sleep(1)
        else:
            self.busy = True
            self.sg.output_query()
            time.sleep(1)
            self.busy = False
            return
