from abc import abstractmethod
from typing import Dict, List, Tuple

from ..device_base import DeviceBase


class Spectrometer(DeviceBase):
    @abstractmethod
    def get_spectra(self) -> Tuple[float, Dict[int, List[float]]]:
        """Timestamp and dict of spectral data for all boards."""
        ...
