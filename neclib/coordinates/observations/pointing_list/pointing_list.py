import importlib

from typing import List, Tuple, Union

import pandas as pd

from abc import ABC, abstractmethod
from pathlib import Path
from astropy import units as u
from astropy.time import Time

from ....core import config
from ...convert import CoordCalculator


class PointingList(ABC):
    def __init__(self, file_name: str, time: Union[float, str], format: str) -> None:
        self.calc = CoordCalculator(config.location)
        self.now = Time(time, format=format)
        self.obsdatetime = self.now.to_datetime()
        self.catalog = self._catalog_to_pandas(file_name=file_name)

    def __new__(cls, model, **kwargs):
        model = config.observatory.upper()
        if model is None:
            raise TypeError(
                f"Cannot instantiate abstract class {cls.__name__!r}. If you need a "
                "dummy version of this class, use `get_dummy` method."
            )

        model = cls._normalize(model)
        if model == cls._normalize(cls.__name__):
            return super().__new__(cls)

        subcls = {cls._normalize(v.__name__): v for v in cls.__subclasses__()}
        if model in subcls:
            return subcls[model](model=model, **kwargs)
        raise ValueError(
            f"Unknown pointing model: {model!r}\n"
            f"Supported ones are: {list(subcls.keys())}"
        )

    @staticmethod
    def _normalize(key: str, /) -> str:
        return key.lower().replace("_", "")

    def readlines_file(self, filename: str) -> List[str]:
        with open(filename, mode="r") as file:
            contents = file.readlines()
        return contents

    def to_altaz(self, target: Tuple[u.Quantity, u.Quantity], frame: str, time=0.0):
        if time == 0.0:
            time = self.now
        coord = self.calc.coordinate(
            lon=target[0], lat=target[1], frame=frame, time=time
        )  # TODO: Consider pressure, temperature, relative_humidity, obswl.
        altaz_coord = coord.to_apparent_altaz()
        return altaz_coord

    @abstractmethod
    def filter(self, magnitude: Tuple[float, float]) -> pd.DataFrame: ...

    @abstractmethod
    def _catalog_to_pandas(self, filename: str): ...


impl = Path(__file__).parent.glob("*.py")
for p in impl:
    if p.name.startswith("_") or p.name == __file__:
        continue
    importlib.import_module(f"{__name__.rsplit('.', 1)[0]}.{p.stem}")
