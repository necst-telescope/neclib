import time
import ogameasure
from ... import config
from .signal_generator_base import SignalGenerator


class FSW0010(SignalGenerator):

    Manufacturer: str = "PhaseMatrix"
    Model = "FSW0010"

    def __init__(self):
        self.busy = False
        com = ogameasure.ethernet(config.rx_fsw0010_host, config.rx_fsw0010_port)
        self.sg = ogameasure.Phasematrix.FSW0010(com)
        self.sg.use_external_reference_source()

    def set_freq(self, freq_GHz):
        while self.busy is True:
            time.sleep(1)
        else:
            self.sg.freq_set(freq_GHz)
            time.sleep(1)
            self.busy = True
            return

    def set_power(self, power_dBm):
        while self.busy is True:
            time.sleep(1)
        else:
            self.sg.power_set(power_dBm)
            time.sleep(1)
            self.busy = True
            return

    def get_freq(self):
        while self.busy is True:
            time.sleep(1)
        else:
            self.sg.freq_query()
            time.sleep(1)
            self.busy = True
            return

    def get_power(self):
        while self.busy is True:
            time.sleep(1)
        else:
            self.sg.power_query()
            time.sleep(1)
            self.busy = True
            return

    def start_output(self):
        while self.busy is True:
            time.sleep(1)
        else:
            self.sg.output_on()
            time.sleep(1)
            self.busy = True
            return

    def stop_output(self):
        while self.busy is True:
            time.sleep(1)
        else:
            self.sg.output_off()
            time.sleep(1)
            self.busy = True
            return

    def get_output_status(self):
        while self.busy is True:
            time.sleep(1)
        else:
            self.sg.output_query()
            time.sleep(1)
            self.busy = True
            return
