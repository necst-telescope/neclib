from typing import Callable, Union

from ...utils import busy, sanity_check
from .da_converter_base import DAConverter


class CPZ340816(DAConverter):

    Manufacturer = "Interface"
    Model = "CPZ340816"

    Identifier = "rsw_id"

    def __init__(self, **kwargs):
        import pyinterface

        self.rsw_id = self.Config.rsw_id
        self.param_buff = {i: 0.0 for i in range(1, 17)}  # All in [V]
        self.da = pyinterface.open(3408, self.rsw_id)

    @property
    def converter(self) -> Callable[[Union[int, float]], float]:
        sanity_check(self.Config.converter, "x")
        return lambda x: eval(self.Config.converter)

    def set_voltage(self, mV: float, id: str) -> None:
        ch = self.Config.channel[id]
        if ch not in self.param_buff.keys():
            raise ValueError(f"Invaild channel {ch}")
        if self.Config.max_mv[0] < mV < self.Config.max_mv[1]:
            raise ValueError(f"Unsafe voltage {mV} mV")
        else:
            self.param_buff[ch] = self.converter(mV)

    def apply_voltage(self) -> None:
        with busy(self, "busy"):
            for i in range(0, 16):
                ch = int(list(self.param_buff.keys())[i])
                voltage = list(self.param_buff.values())[i]

                self.da.output_da(ch, voltage)

    def finalize(self) -> None:
        self.da.finalize()
        self.param_buff = {i: 0.0 for i in range(1, 17)}