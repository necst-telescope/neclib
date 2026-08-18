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
        self._max_ch = 2**15
        self._record_ch = self._max_ch
        _rand = Random(limits=(0, 1e13)).walk(1e10, 1e2, -10)
        initial = [next(_rand) for _ in range(self._max_ch)]
        self._rand = Random().walk(1e10, 1, -1, initial=initial)

    @property
    def _board_ids(self) -> List[int]:
        """Return board IDs enabled by the bound spectrometer configuration."""
        bw_mhz = getattr(self.Config, "bw_MHz", None)
        if not bw_mhz:
            return [0]
        return [int(board_id) for board_id in bw_mhz]

    def get_spectra(self) -> Tuple[float, str, Dict[int, List[float]]]:
        """Return timestamped synthetic spectra for all configured boards."""
        timestamp = time.time()
        data = {
            board_id: next(self._rand).tolist()[: self._record_ch]
            for board_id in self._board_ids
        }
        return timestamp, str(timestamp), data

    def change_spec_ch(self, chan: int) -> None:
        """Change the number of channels returned by the simulated spectrometer."""
        chan = int(chan)
        if not 1 <= chan <= self._max_ch:
            raise ValueError(
                f"Simulated spectrometer channel count must be 1-{self._max_ch}: {chan}"
            )
        self._record_ch = chan

    def finalize(self) -> None:
        pass
