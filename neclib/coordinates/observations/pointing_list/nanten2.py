from typing import Tuple

import pandas as pd

from astropy.coordinates import Angle
from astropy import units as u

from ....core import config
from .pointing_list import PointingList


class NANTEN2(PointingList):
    def _catalog_to_pandas(self, filename: str):
        pass

    def filter(self, magnitude: Tuple[float, float]) -> pd.DataFrame:
        pass
