from typing import Callable, Dict, List

import astropy.units as u

from ...utils import busy, sanity_check
from .ad_converter_base import ADConverter


class CPZ3177(ADConverter):

    """a/d converter, which can convert by 32 or 64 channels.

    Notes
    -----
    Configuration items for this device:

    rsw_id : {0, 1, ..., 16} or {"0", "1", ..., "9", "A", ..., "F"}
        Board identifier. This should be set to the same value as the rotary switch
        "RSW1" mounted on the side of the board. The board is shipped with default RSW1
        setting of 0. This ID would be non-zero, when multiple PCI board of same model
        are mounted on a single FA (Factory Automation) controller.

    ave_num : int
        Sampling data number to calculate average of data. This source code not only
        measure the actual voltage, but also calculate the average of data
        in order to measure a faint voltage. It should not be define too large number
        against sampling frequency.

    smpl_freq : int
        Sampling frequency. Number of measuring data per 1 second.
        It should not be too small number against number of data for
        calculating average.

    single_diff : {"SINGLE" or "DIFF"}
        Input type of voltage. "SINGLE" is Single-ended input, "DIFF" is
        "Differential input".

    all_ch_num : int
        Number of channel using for measuring voltage. This number must be  the same
        as the number of setting channel in smpl_ch_req. The maximum number is
        32 in differential input, 64 in single-ended input. Please read the manual
        of this board for wiring design.

    smpl_ch_req : List[Dict[str, int], Dict[str, int]...]
        List of measuring range. The number of setting channel must be the same as
        all_ch_num. In addition, it must be defined ch1 through the maximum used
        channel number. For example, channel number: 3, 5, 9, 12 are used, then
        smpl_ch_req must be set ch1 through ch12.

    channel : Dict[str, int]
        Detail channel name to measure and connecting channel number.
        It can be define any name. It does not have to define all channel which
        setting in smpl_ch_req. It should be defined the used channels in minimum.

    converter : Dict[str, int]
        Function from actual voltage to value you want. This configuration
        is used when the actual voltage are converted other values by any function.

    """

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
