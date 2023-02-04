from typing import Callable, Dict, List

import astropy.units as u

from ...core import logic
from ...core.security import sanitize
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
        Number of sampled data to be averaged over. This script not only measures the
        actual voltage, but also performs fluctuation reduction in order to measure a
        faint voltage. The value should not be too large compared to sampling frequency
        ``smpl_freq``, otherwise the output won't follow the change of voltage.

    smpl_freq : int
        Sampling frequency; number of data obtained in 1 second. The value should not
        be too small against ``ave_num``.

    single_diff : {"SINGLE" or "DIFF"}
        Input type of voltage. "SINGLE" is Single-ended input, "DIFF" is
        "Differential input".

    all_ch_num : int
        Number of channels used in voltage measurement. This number must be the same
        as the number of channels defined for ``smpl_ch_req``. The maximum number is
        32 in differential input, 64 in single-ended input. Please read the manual
        of this board for wiring design.

    smpl_ch_req : List[Dict[str, Union[int, str]]]
        List of measurement range, in format
        ``{ ch_no = int(channel_number), range = str(range_specifier) }``. The length of
        the list must be the same as ``all_ch_num``. In addition, it must be defined
        from ch1 through the maximum channel number to be used. For example, when
        channels [3, 5, 9, 12] are used, ``smpl_ch_req`` must be set from ch1 through
        ch12. The acceptable "range" values are as below:
        '0_5V': 0 - 5 V
        '010V' : 0 - 10 V
        '2P5V' : -2.5 - 2.5 V
        '5V' : -5 - 5 V
        '10v' : -10 - 10 V
        These should be set to the same value as the value corresponding to combination
        of three DIP switch "DSW1", "DSW2", "DSW3" mounted on the side of the board.
        Please read the manual of this board for the combination of DIP switches.

    channel : Dict[str, int]
        Human-readable channel name. The value should be mapping from human readable
        version (str) to device level identifier (int). You can assign any name to the
        channels. No need to define the aliases for all the channels listed in
        ``smpl_ch_req``, but defining aliases for unused channels will raise error.

    converter : Dict[str, str]
        Functions to convert measured voltage to any parameter you want, in format
        ``{str(parameter_type) = str(function)}``. Supported ``parameter_types`` are
        ["V", "I", "P"], and ``x`` in ``function`` will be substituted by the measured
        value. This would be useful when measured voltage is scaled and/or shifted
        version of phisical parameter.

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
        with logic.busy(self, "busy"):
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
        _ = [sanitize(expr, "x") for expr in self.Config.converter.values()]
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
