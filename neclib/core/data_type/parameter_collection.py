"""Interface to access NECLIB parameters.

This module defines the NECLIB standard parameter interface. The values can be any
Python built-in type, or physical quantity which need units specified.

The parameters would be stored in TOML files, in the following format:

```toml
[parameter_kind]
parameter_name = value

[another_parameter_kind]
"parameter_with_units[units]" = value
parameter_without_units = value
```

The parameters should be grouped by their kind, which is specified by the TOML table
name. This kind won't be kept in the parameter interface, but we require its use to
keep the parameter files readable.

"""

import os
import re
from typing import IO, Any, List, Tuple, Union

import astropy.units as u
from astropy.coordinates import Angle
from tomlkit import parse
from tomlkit.toml_file import TOMLFile

from .formatting import html_repr_of_dict


class Parameters:
    """Parser for NECLIB parameters files.

    This class provides a convenient interface to access the parameters, whose values
    can be physical quantities; which contain units. The parameters can be stored in
    TOML files, so this class also provides a its parser.

    Examples
    --------
    If the parameters are stored in a TOML file, use `from_file` method:
    >>> from neclib.parameters import Parameters
    >>> params = Parameters.from_file("parameters.toml")
    >>> params["distance"]
    <Quantity 10. pc>

    You can also provide the parameters as keyword arguments, but physical units may not
    be parsed:
    >>> params = Parameters(distance="10 pc")
    >>> params["distance"]
    "10 pc"

    To parse the units, use the following syntax:
    >>> params = Parameters(**{"distance[pc]": 10})
    >>> params["distance"]
    <Quantity 10. pc>

    Of course you can provide many parameters at once:
    >>> params = Parameters(**{"distance[pc]": 10, "inclination[deg]": 45})
    >>> params["distance"]
    <Quantity 10. pc>

    You can also access the parameters as attributes:
    >>> params.distance
    <Quantity 10. pc>

    Notes
    -----
    The units are parsed using `astropy.units` and `astropy.coordinates.Angle`. The
    units are parsed from the parameter name, so the parameter name must be in the
    following format: `parameter_name[unit]`.

    """

    __slots__ = ("_parameters", "_path")

    _unit_matcher = re.compile(r"(\w*)\[([\w/\s\*\^-]*)\]")
    _angle_units: List[str] = [unit.name for unit in u.rad.find_equivalent_units()] + [
        alias for unit in u.rad.find_equivalent_units() for alias in unit.aliases
    ]

    def __init__(self, **kwargs) -> None:
        raw_params = kwargs
        self._parameters = dict(
            map(self._parse, raw_params.keys(), raw_params.values())
        )
        self._path = None

    @classmethod
    def from_file(cls, file: Union[os.PathLike, str, IO]):
        if isinstance(file, IO):
            params = parse(file.read())
            return cls(**params)
        else:
            _params = TOMLFile(file).read().unwrap()
            params = {}
            _ = [params.update(x) for x in _params.values()]
            inst = cls(**params)
            inst._path = file
            return inst

    def __str__(self) -> str:
        width = max(len(x) for x in self._parameters)
        params = [
            f"{k:{width}s} = {v} ({type(v).__name__})"
            for k, v in self._parameters.items()
        ]
        return self.__class__.__name__ + "\n" + "\n".join(params)

    def __repr__(self) -> str:
        return self.__class__.__name__ + f"({len(self._parameters)} parameters)"

    def _repr_html_(self) -> str:
        return html_repr_of_dict(
            self._parameters, type(self), metadata={"File": self._path}
        )

    def _parse(self, k: str, v: Any) -> Tuple[str, Any]:
        if (k in self.__class__.__dict__) or (k in self.__slots__):
            raise AttributeError(f"Attribute {k} already exists")

        if v == {}:
            v = None
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
        if key in self._parameters:
            return self._parameters[key]

    def __getattr__(self, key: str) -> Any:
        if key in self._parameters:
            return self._parameters[key]

    @property
    def parameters(self) -> dict:
        return self._parameters.copy()
