import time

import numpy as np


class CutSpectralData:
    def __init__(self) -> None:
        self.msg_list = []

    def update(self, msg: list):
        self.msg_list.append(msg)
        if len(self.msg_list) > 1:
            while self.msg_list[0].time < time.time() - 1:
                self.msg_list.pop(0)

    def cut(self, min_index: int, max_index: int):
        """Cut spectral data with arbitrary range.

        Parameter
        ---------
        min_index
            The initial index of spectral data you want.
        max_index
            The last index of spectral data you want.

        Example
        -------
        >>> spectral_data = neclib.data.CutSpectralData()
        >>> spectral_data.update(msg)
        Repeat several times ...
        >>> spectral_data.cut(8192, 16384)
        """
        spec_array = np.array([msg.data for msg in self.msg_list])
        cut_spec_array = spec_array[:, min_index : max_index + 1]
        return cut_spec_array.mean(axis=0).tolist()
