import pyinterface

from ...utils import busy
from .bias_setter_base import BiasSetter


class CPZ340816(BiasSetter):

    Manufacturer = "pyinterface"
    Model = "CPZ340816"

    Identifier = "rsw_id"

    def __init__(self):
        self.rsw_id = self.Config.rsw_id
        self.param_buff = {
            1: 0.0,
            2: 0.0,
            3: 0.0,
            4: 0.0,
            5: 0.0,
            6: 0.0,
            7: 0.0,
            8: 0.0,
            9: 0.0,
            10: 0.0,
            11: 0.0,
            12: 0.0,
            13: 0.0,
            14: 0.0,
            15: 0.0,
            16: 0.0,
        }  # All in [V]
        self.da = pyinterface.open(3408, self.rsw_id)

    def set_voltage(self, voltage_mV: float, ch: int) -> None:
        if ch not in self.param_buff.keys():
            raise ValueError("Invaild channel {ch}")
        else:
            self.param_buff[ch] = voltage_mV / 3

    def output_voltage(self) -> None:
        with busy(self, "busy"):
            for i in range(0, 16):
                ch = int(list(self.param_buff.keys())[i])
                voltage = list(self.param_buff.values())[i]

                self.da.output_da(ch, voltage)

                continue

    def finalize(self) -> None:
        self.da.finalize()
        self.param_buff = {
            1: 0.0,
            2: 0.0,
            3: 0.0,
            4: 0.0,
            5: 0.0,
            6: 0.0,
            7: 0.0,
            8: 0.0,
            9: 0.0,
            10: 0.0,
            11: 0.0,
            12: 0.0,
            13: 0.0,
            14: 0.0,
            15: 0.0,
            16: 0.0,
        }
