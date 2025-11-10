import time
from typing import Callable, Union

from ...core.security import busy
from .da_converter_base import DAConverter


class Setter_2450(DAConverter):
    Manufacturer = "Keithley"
    Model = "2450"

    def __init__(self):
        self.rsw_id = self.Config.rsw_id
        self.param_buff = {i: 0.0 for i in range(1, 17)}

    @property
    def converter(self) -> Callable[[Union[int, float]], float]:
        conv = {}
        for k, v in self.Config.converter.items():
            _ = sanitize(v, "x")
            conv[k] = eval(f"lambda x: {v}")
        return conv

    def set_voltage(self, mV: float, id: str) -> None:
        ch = self.Config.channel[id]
        if ch not in self.param_buff.keys():
            raise ValueError(f"Invaild channel {ch}")
        if not self.Config.max_mv[0] < mV < self.Config.max_mv[1]:
            raise ValueError(f"Unsafe voltage {mV} mV")
        else:
            self.param_buff[ch] = self.converter[id](mV)

    def apply_voltage(self) -> None:
        with busy(self, "busy"):
            for i in range(0, 16):
                ch = int(list(self.param_buff.keys())[i])
                voltage = list(self.param_buff.values())[i]
                self.da.output_da(ch, voltage)
                time.sleep(0.001)

    def finalize(self) -> None:
        self.da.finalize()
        self.param_buff = {i: 0.0 for i in range(1, 17)}

    def close(self) -> None:
        pass
