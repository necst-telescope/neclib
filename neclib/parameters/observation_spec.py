import os
import re
from typing import Any, Tuple, Union

import astropy.units as u
from astropy.coordinates import Angle
from tomlkit.toml_file import TOMLFile


class ObservationSpec:

    _unit_matcher = re.compile(r"(\w*)\[([\w]*)\]")
    _angle_units = [unit.name for unit in u.rad.find_equivalent_units()] + [
        alias for unit in u.rad.find_equivalent_units() for alias in unit.aliases
    ]

    def __init__(self, **kwargs) -> None:
        raw_params = {}
        _ = [raw_params.update(v) for v in kwargs.values()]
        self._parameters = dict(
            map(self._parse, raw_params.keys(), raw_params.values())
        )

    @classmethod
    def from_file(cls, path: Union[os.PathLike, str]) -> "ObservationSpec":
        params = TOMLFile(path).read().unwrap()
        return cls(**params)

    def __str__(self) -> str:
        width = max(len(x) for x in self._parameters)
        params = [
            f"{k:{width}s} = {v} ({type(v).__name__})"
            for k, v in self._parameters.items()
        ]
        return self.__class__.__name__ + "\n" + "\n".join(params)

    def __repr__(self) -> str:
        return self.__class__.__name__ + f"({len(self._parameters)} parameters)"

    def _parse(self, k: str, v: Any) -> Tuple[str, Any]:
        if k in self.__class__.__dict__:
            raise AttributeError(f"Attribute {k} already exists")

        if v == {}:
            return k, None
        unit_match = self._unit_matcher.match(k)
        if unit_match is None:
            return k, v

        key, unit = unit_match.groups()
        if key in self.__class__.__dict__:
            raise AttributeError(f"Attribute {key} already exists")

        if unit in self._angle_units:
            return key, Angle(v, unit=unit)
        return key, u.Quantity(v, unit=unit)

    def __getitem__(self, key: str) -> Any:
        return self._parameters[key]

    def __getattr__(self, key: str) -> Any:
        return self._parameters[key]
