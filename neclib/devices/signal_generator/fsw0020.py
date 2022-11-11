import astropy.units as u
import time
import ogameasure
from ... import config
from .signal_generator_base import SignalGenerator


class FSW0020(SignalGenerator):

    Manufacturer: str = "PhaseMatrix"
    Model = "FSW0020"

    def __init__(self):
        self.busy = False
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
        """Set the power of the signal generator output.

        Attention
        ---------
        The ability to change power of this signal generator is optional configuration.
        For products without the option, this function has no effect but raises no
        error.

        """
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
            f = self.sg.freq_query()
            time.sleep(1)
            self.busy = False
            return f * u.Hz

    def get_power(self):
        """Get the power of the signal generator output.

        Attention
        ---------
        The ability to change power of this signal generator is optional configuration.
        For products without the option, this function may return meaningless value.

        """
        while self.busy is True:
            time.sleep(1)
        else:
            self.busy = True
            f = self.sg.power_query()
            time.sleep(1)
            self.busy = False
            return f * u.dB(u.mW)

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
            f = self.sg.output_query()
            time.sleep(1)
            self.busy = False
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
