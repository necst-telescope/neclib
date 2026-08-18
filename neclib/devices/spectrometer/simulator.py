import math
import time
from typing import Dict, List, Mapping, Sequence, Tuple

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

        # Approximate a spectrometer while keeping all source-state behaviour
        # simulator-only.  NECST decides *when* the observation is ON/OFF/HOT and
        # passes already resolved channel-domain line components to this class.
        self._baseline = 1e10
        self._white_noise_fraction = 0.02
        self._gain = 1.0
        self._gain_step_sigma = 2e-4
        self._gain_restore = 0.02
        self._rng = np.random.default_rng()
        self._board_scale: Dict[int, float] = {}
        self._hot = False
        self._on_source = False
        self._on_line_components: Dict[int, List[Dict[str, float]]] = {}
        self._channel_index = np.arange(self._max_ch, dtype=float)

        # These parameters are simulator-only.  The baseline represents the SKY
        # state, and HOT/ON are expressed as additional input temperature.
        self._t_rx_K = float(getattr(self.Config, "simulator_t_rx_K", 150.0))
        self._t_sky_K = float(getattr(self.Config, "simulator_t_sky_K", 70.0))
        self._t_hot_K = float(getattr(self.Config, "simulator_t_hot_K", 293.0))
        if self._t_rx_K < 0 or self._t_sky_K < 0 or self._t_hot_K < 0:
            raise ValueError("Simulator temperatures must be non-negative")
        if self._t_rx_K + self._t_sky_K <= 0:
            raise ValueError("simulator_t_rx_K + simulator_t_sky_K must be positive")

    @property
    def _board_ids(self) -> List[int]:
        """Return board IDs enabled by the bound spectrometer configuration."""
        bw_mhz = getattr(self.Config, "bw_MHz", None)
        if not bw_mhz:
            return [0]
        return [int(board_id) for board_id in bw_mhz]

    @property
    def hot_factor(self) -> float:
        """Return HOT/SKY power ratio for the configured simulator temperatures."""
        return (self._t_rx_K + self._t_hot_K) / (self._t_rx_K + self._t_sky_K)

    def set_hot(self, enabled: bool) -> None:
        """Select the simulator-only HOT-load state."""
        self._hot = bool(enabled)

    def set_on_source(self, enabled: bool) -> None:
        """Enable or disable source-line emission for simulator ON integrations."""
        self._on_source = bool(enabled)

    def set_on_line_components(
        self, components_by_board: Mapping[int, Sequence[Mapping[str, float]]]
    ) -> None:
        """Replace simulator ON-line components in full-channel coordinates.

        Parameters
        ----------
        components_by_board
            Mapping from raw board ID to Gaussian components.  Each component
            contains ``center_channel`` (fractional full-channel index),
            ``fwhm_channels`` (> 0), and ``t_line_peak_K`` (>= 0).

        Notes
        -----
        This interface deliberately knows nothing about ROS, window IDs, rest
        frequencies, velocity frames, or LO chains.  NECST resolves those
        observation-level concepts before calling this method.
        """
        normalized: Dict[int, List[Dict[str, float]]] = {}
        for raw_board_id, raw_components in components_by_board.items():
            board_id = int(raw_board_id)
            board_components: List[Dict[str, float]] = []
            for raw in raw_components:
                center = float(raw["center_channel"])
                fwhm = float(raw["fwhm_channels"])
                peak = float(raw["t_line_peak_K"])
                if not math.isfinite(center):
                    raise ValueError("center_channel must be finite")
                if not math.isfinite(fwhm) or fwhm <= 0:
                    raise ValueError("fwhm_channels must be positive finite")
                if not math.isfinite(peak) or peak < 0:
                    raise ValueError("t_line_peak_K must be non-negative finite")
                board_components.append(
                    {
                        "center_channel": center,
                        "fwhm_channels": fwhm,
                        "t_line_peak_K": peak,
                    }
                )
            normalized[board_id] = board_components
        self._on_line_components = normalized

    def _next_gain(self) -> float:
        """Return slowly varying common gain around unity."""
        self._gain += self._gain_restore * (1.0 - self._gain)
        self._gain += float(self._rng.normal(0.0, self._gain_step_sigma))
        self._gain = float(np.clip(self._gain, 0.98, 1.02))
        return self._gain

    def _line_temperature(self, board_id: int) -> np.ndarray:
        """Return summed ON-line antenna temperature for one raw board."""
        line_temperature = np.zeros(self._max_ch, dtype=float)
        for component in self._on_line_components.get(int(board_id), []):
            center = component["center_channel"]
            fwhm = component["fwhm_channels"]
            peak = component["t_line_peak_K"]
            line_temperature += peak * np.exp(
                -4.0
                * math.log(2.0)
                * ((self._channel_index - center) / fwhm) ** 2
            )
        return line_temperature

    def _load_scale(self, board_id: int):
        """Return channel-wise input-temperature scale relative to SKY."""
        if self._hot:
            # The inserted load blocks the sky, so a stale ON state must never
            # superpose an astronomical line on the HOT spectrum.
            return self.hot_factor
        if not self._on_source:
            return 1.0
        line_temperature = self._line_temperature(board_id)
        return 1.0 + line_temperature / (self._t_rx_K + self._t_sky_K)

    def _spectrum(self, board_id: int, gain: float) -> List[float]:
        """Generate broadband noise and simulator-only state signal for one board."""
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
            * self._load_scale(board_id)
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
