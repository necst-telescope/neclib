from abc import abstractmethod
from typing import Dict, List, Tuple

from ..device_base import DeviceBase

import numpy as np


class Spectrometer(DeviceBase):
    @abstractmethod
    def get_spectra(self) -> Tuple[float, Dict[int, List[float]]]:
        """Timestamp and dict of spectral data for all boards."""
        ...

    def calc_tp(data: Dict[int, List[float]]) -> float:
        return np.nansum(data[1])
