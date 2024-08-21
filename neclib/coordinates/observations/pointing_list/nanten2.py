from .pointing_list import PointingList


class NANTEN2(PointingList):
    def _catalog_to_pandas(self, filename: str):
        pass

    def filter(self, magnitude: Tuple[float, float]) -> pd.DataFrame:
        pass
