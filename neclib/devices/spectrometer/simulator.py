import time
from typing import Dict, List, Tuple

import numpy as np

from .spectrometer_base import Spectrometer


class SpectrometerSimulator(Spectrometer):
    Manufacturer: str = ""
    Model: str = ""
    Identifier = ""
    is_simulator = True

    def __init__(self) -> None:
        self._max_ch = 2**15
        self._record_ch = self._max_ch

        # Approximate a spectrometer without attaching any observing-state meaning
        # to the synthetic data.  ON/OFF/HOT behaviour can be layered on top later.
        self._baseline = 1e10
        self._white_noise_fraction = 0.02
        self._gain = 1.0
        self._gain_step_sigma = 2e-4
        self._gain_restore = 0.02
        self._rng = np.random.default_rng()
        self._board_scale: Dict[int, float] = {}

    @property
    def _board_ids(self) -> List[int]:
        """Return board IDs enabled by the bound spectrometer configuration."""
        bw_mhz = getattr(self.Config, "bw_MHz", None)
        if not bw_mhz:
            return [0]
        return [int(board_id) for board_id in bw_mhz]

    def _next_gain(self) -> float:
        """Return slowly varying common gain around unity."""
        self._gain += self._gain_restore * (1.0 - self._gain)
        self._gain += float(self._rng.normal(0.0, self._gain_step_sigma))
        self._gain = float(np.clip(self._gain, 0.98, 1.02))
        return self._gain

    def _spectrum(self, board_id: int, gain: float) -> List[float]:
        """Generate broadband noise for one simulated spectrometer board."""
        if board_id not in self._board_scale:
            self._board_scale[board_id] = float(self._rng.normal(1.0, 0.01))

        white_noise = self._rng.normal(
            0.0,
            self._white_noise_fraction,
            self._max_ch,
        )
        spectrum = (
            self._baseline
            * self._board_scale[board_id]
            * gain
            * (1.0 + white_noise)
        )
        return spectrum[: self._record_ch].tolist()

    def get_spectra(self) -> Tuple[float, str, Dict[int, List[float]]]:
        """Return timestamped synthetic spectra for all configured boards."""
        timestamp = time.time()
        gain = self._next_gain()
        data = {
            board_id: self._spectrum(board_id, gain) for board_id in self._board_ids
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
