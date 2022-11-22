import pyinterface
import astropy.units as u

from ... import config
from ...devices import utils

from .bias_reader_base import BiasReader


class CPZ3177(BiasReader):
    Manufacturer = "Interface"
    Model = "CPZ3177"

    Identifier = config.rx_cpz3177_rsw_id

    def __init__(self) -> None:

        self.ave_num = rospy.get_param("~ave_num")
        self.smpl_freq = rospy.get_param("~smpl_freq")

        self.ad = pyinterface.open(3177, config.rx_cpz3177_rsw_id)
        self.ad.stop_sampling()
        self.ad.initialize()
        self.ad.set_sampling_config(
            smpl_ch_req=smpl_ch_req,
            smpl_num=1000,
            smpl_freq=self.smpl_freq,
            single_diff=single_diff,
            trig_mode="ETERNITY",
        )
        self.ad.start_sampling("ASYNC")

    def get_data(self) -> u.Quantity:
        with utils.busy(self, "busy"):
            offset = self.ad.get_status()["smpl_count"] - self.ave_num
            data = self.ad.read_sampling_buffer(self.ave_num, offset)
            data_li_2 = []
            for i in range(all_ch_num):
                data_li = []
                for k in range(self.ave_num):
                    data_li.append(data[k][i])
                data_li_2.append(data_li)

            ave_data_li = []
            for data in data_li_2:
                d = sum(data) / self.ave_num
                ave_data_li.append(d)
            return ave_data_li
