from typing import Callable, Dict, List

import astropy.units as u

from ...utils import busy, sanity_check
from .ad_converter_base import ADConverter


class CPZ3177(ADConverter):
    Manufacturer = "Interface"
    Model = "CPZ3177"

    Identifier = "rsw_id"

    def __init__(self, **kwargs) -> None:
        import pyinterface

        self.rsw_id = self.Config.rsw_id
        self.ave_num = self.Config.ave_num
        self.smpl_freq = self.Config.smpl_freq
        self.single_diff = self.Config.single_diff
        self.all_ch_num = self.Config.all_ch_num
        self.smpl_ch_req = self.Config.smpl_ch_req

        self.ad = pyinterface.open(3177, self.rsw_id)
        self.ad.stop_sampling()
        self.ad.initialize()
        self.ad.set_sampling_config(
            smpl_ch_req=self.smpl_ch_req,  # It must be a list
            smpl_num=1000,
            smpl_freq=self.smpl_freq,
            single_diff=self.single_diff,
            trig_mode="ETERNITY",
        )
        self.ad.start_sampling("ASYNC")

    def get_data(self, ch: int) -> List[float]:
        with busy(self, "busy"):
            offset = self.ad.get_status()["smpl_count"] - self.ave_num
            data = self.ad.read_sampling_buffer(self.ave_num, offset)
            data_li_2 = []
            for i in range(self.all_ch_num):
                data_li = []
                for k in range(self.ave_num):
                    data_li.append(data[k][i])
                data_li_2.append(data_li)

            ave_data_li = []
            for data in data_li_2:
                d = sum(data) / self.ave_num
                ave_data_li.append(d)
            return ave_data_li[ch - 1]

    @property
    def converter(self) -> Dict[str, Callable[[float], float]]:
        _ = [sanity_check(expr, "x") for expr in self.Config.converter.values()]
        return {k: eval(f"lambda x: {v}") for k, v in self.Config.converter.items()}

    def get_voltage(self, id: str) -> u.Quantity:
        ch = self.Config.channel[id]
        return self.converter["V"](self.get_data(ch)) * u.mV

    def get_current(self, id: str) -> u.Quantity:
        ch = self.Config.channel[id]
        return self.converter["I"](self.get_data(ch)) * u.microampere

    def get_power(self, id: str) -> u.Quantity:
        ch = self.Config.channel[id]
        return self.converter["P"](self.get_data(ch)) * u.mW

    def finalize(self) -> None:
        self.ad.stop_sampling()
