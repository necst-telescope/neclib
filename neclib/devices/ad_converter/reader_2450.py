from typing import Callable, Dict, List

import astropy.units as u

from ...core.security import busy
from .ad_converter_base import ADConverter
import ogameasure


class Reader_2450(ADConverter):
    Manufacturer = "Keithley"
    Model = "2450"

    def __init__(self) -> None:
        com = ogameasure.ethernet(self.Config.host, self.Config.port)
        self.source_meter = ogameasure.device.Keithley.Keithley_2450(com)
        self.channel = self.Config.channel
        self.conv = self.Config.converter
        self.all_ch_num = self.Config.all_ch_num

    def get_data(self) -> List[float]:
        """
        get data that was calculated in the designed range
        """
        with busy(self, "busy"):
            data = []
            data.append(self.source_meter.voltage_query())
            data.append(self.source_meter.current_query())
        return data

    def converter(self) -> Dict[str, Callable[[float], float]]:
        """
        change the format from the imported one in the config
        """
        conv = []
        for i in self.Config.converter:
            conv.append({k: v for k, v in i.items()})
        return conv

    def get_all(self, target: str) -> dict:
        """
        put data from each channel into DICT format
        """
        data = self.get_data()
        data_dict = {}
        filtered_conv = list(
            filter(lambda item: item["ch"].startwith(target), self.converter)
        )
        for i in filtered_conv:
            ch = self.Config.channel[i["ch"]]
            value = data[ch - 1]
            data_dict[i["ch"]] = u.Quantity(value, i["units"])
        return data_dict

    def get_from_id(self, id: str) -> u.Quantity:
        ch: int = self.Config.channel[id]
        di_search: dict = list(filter(lambda item: item["ch"] == id, self.converter))[0]
        value = self.get_data()[ch - 1]
        return u.Quantity(value, di_search["units"])

    def set_voltage(self, mV: float, id: str ) -> None:
        if id not in self.Config.channel.keys():
            raise ValueError(f"Invaid channel {id}")
        if not self.Config.max_mv[0] < mV < self.Config.max_mv[1]:
            raise ValueError(f"Unsafe voltage {mV} mV")
        else:
            self.source_meter.set_voltage(mV)

    def finalize(self):
        self.source_meter.output_off()
        try:
            self.source_meter.com.close()
        except AttributeError:
            pass

    def close(self) -> None:
        self.finalize()
