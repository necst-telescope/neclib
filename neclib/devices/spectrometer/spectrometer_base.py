from abc import abstractmethod
from typing import Dict, List, Tuple

from ..device_base import DeviceBase

import numpy as np


class Spectrometer(DeviceBase):
    @abstractmethod
    def get_spectra(self) -> Tuple[float, Dict[int, List[float]]]:
        """Timestamp and dict of spectral data for all boards."""
        ...

    def calc_tp(self, data: Dict[int, Tuple[float]], tp_range: List[int]) -> dict:
        tp_dict = {}
        if tp_range:
            for board_id, spectral_data in data.items():
                for i in range(0, len(tp_range), 2):
                    tp = np.nansum(spectral_data[tp_range[i] : tp_range[i+1]])
                    tp_list = [np.float32(tp)]
                    tp_dict[board_id] += tp_list
        else:
            for board_id, spectral_data in data.items():
                tp = np.nansum(spectral_data)
                tp_list = [np.float32(tp)]
                tp_dict[board_id] = tp_list
        return tp_dict
