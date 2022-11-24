import pyinterface
import astropy.units as u

from ...devices import utils

from .bias_reader_base import BiasReader


class CPZ3177(BiasReader):
    Manufacturer = "Interface"
    Model = "CPZ3177"

    Identifier = "rsw_id"

    def __init__(self) -> None:

        self.rsw_id = self.Config.rsw_id
        self.ave_num = self.Config.ave_num
        self.smpl_freq = self.Config.smpl_freq
        self.single_diff = self.Config.single_diff
        self.all_ch_num = self.Config.all_ch_num

        self.ad = pyinterface.open(3177, self.rsw_id)
        self.ad.stop_sampling()
        self.ad.initialize()
        self.ad.set_sampling_config(
            smpl_ch_req=smpl_ch_req,  # imcomplete. Add list?
            smpl_num=1000,
            smpl_freq=self.smpl_freq,
            single_diff=self.single_diff,
            trig_mode="ETERNITY",
        )
        self.ad.start_sampling("ASYNC")

    def get_data(self) -> u.Quantity:
        with utils.busy(self, "busy"):
            offset = self.ad.get_status()["smpl_count"] - self.ave_num
            data = self.ad.read_sampling_buffer(self.ave_num, offset)
            data_li_2 = []
            for i in range(self.all_ch_num):
                data_li = []
                for k in range(self.ave_num):
                    data_li.append(data[k][i])
                data_li_2.append(data_li)

            ave_data_li = []
            for (
                data
            ) in (
                data_li_2
            ):  # run "for" in range of the length of data_li_2(=all_ch_num?) Is "data" a list?
                d = sum(data) / self.ave_num  # Cal average
                ave_data_li.append(d)  # Add average to returned list
            return ave_data_li  # what value is this in the list? voltage? current?
