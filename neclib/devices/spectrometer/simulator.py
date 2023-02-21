import time
from typing import Dict, List, Tuple

from ...core.math import Random
from .spectrometer_base import Spectrometer


class SpectrometerSimulator(Spectrometer):
    Manufacturer: str = ""
    Model: str = ""
    Identifier = ""
    is_simulator = True

    def __init__(self) -> None:
        _rand = Random(limits=(0, 1e13)).walk(1e10, 1e2, -10)
        initial = [next(_rand) for _ in range(2**15)]
        self._rand = Random().walk(1e10, 1, -1, initial=initial)

    def get_spectra(self) -> Tuple[float, Dict[int, List[float]]]:
        """Timestamp and dict of spectral data for all boards."""
        return time.time(), {0: next(self._rand).tolist()}

    def finalize(self) -> None:
        pass
