import time
from typing import Optional, Tuple

import numpy as np


class Resize:
    def __init__(self, keep_duration_sec: float = 1.0) -> None:
        self.data_list = []
        self.keep_duration = keep_duration_sec

    def push(self, data: list, timestamp: Optional[float] = None) -> None:
        timestamp = time.time() if timestamp is None else timestamp
        self.data_list.append((data, timestamp))
        self._discard_outdated_data()

    def _discard_outdated_data(self) -> None:
        now = time.time()
        self.data_list.sort(key=lambda x: x[1])
        while (len(self.data_list) > 1) and (
            self.data_list[0][1] < now - self.keep_duration
        ):
            self.data_list.pop(0)
        while (len(self.data_list) > 1) and (
            len(self.data_list[-1][0]) != len(self.data_list[0][0])
        ):
            self.data_list.pop(0)

    def get(self, range: Tuple[int, int], n_samples: Optional[int] = None) -> list:
        """Cut spectral data with arbitrary range.

        Parameter
        ---------
        range
            The first and last index of spectral data you want (last index won't be
            included).
        n_samples
            The number of (coarse) samples you want.

        Example
        -------
        >>> spectral_data = neclib.data.Resize()
        >>> spectral_data.push(data)
        Repeat several times ...
        >>> spectral_data.get([8192, 16384], 100)

        """
        self._discard_outdated_data()
        spec_array = np.array([data[0] for data in self.data_list])

        cut_spec_array = spec_array[:, slice(*range)].mean(axis=0)
        # Validity of taking mean at this point (before interpolation) isn't checked,
        # just for simple implementation using `np.interp`.
        # Out-of-range slice index won't raise any error, due to permissive NumPy
        # indexing, i.e., `range=(-99999, 99999)` is valid though the output won't be
        # what you desire.

        if n_samples is not None:
            target_idx = np.linspace(0, len(cut_spec_array), n_samples)
            original_idx = np.linspace(0, len(cut_spec_array), len(cut_spec_array))
            cut_spec_array = np.interp(target_idx, original_idx, cut_spec_array)
        return cut_spec_array.tolist()
