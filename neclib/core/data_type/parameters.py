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
import warnings
from typing import IO, Any, Dict, List, Tuple, Union

import astropy.units as u
from astropy.coordinates import Angle
from tomlkit import parse
from tomlkit.toml_file import TOMLFile

from ...exceptions import NECSTAccessibilityWarning
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
        self._aliases: Dict[str, str] = {}

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

    def attach_alias(self, **kwargs: str) -> None:
        for k, v in kwargs.items():
            self._validate(k)
            if k not in self._parameters:
                raise KeyError(f"Unknown parameter: {k!r}")
            if v in self._parameters:
                raise KeyError(
                    f"Cannot create alias with existing parameter name: {v!r}"
                )
            if v not in self._aliases:
                self._aliases[v] = k

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
            self._parameters,
            type(self),
            aliases=self._aliases,
            metadata={"File": self._path},
        )

    def _validate(self, key: str) -> None:
        if (key in self.__class__.__dict__) or (key in self.__slots__):
            raise AttributeError(f"Reserved name: {key!r}")
        if not key.isidentifier():
            warnings.warn(
                f"{key!r} isn't a valid Python identifier, "
                "so attribute access isn't available.",
                NECSTAccessibilityWarning,
            )

    def _parse(self, k: str, v: Any) -> Tuple[str, Any]:
        if v == {}:
            v = None

        unit_match = self._unit_matcher.match(k)
        if unit_match is None:
            self._validate(k)
            return k, v

        key, unit = unit_match.groups()
        self._validate(key)
        if unit in self._angle_units:
            return key, Angle(v, unit=unit)
        return key, u.Quantity(v, unit=unit)

    def __getitem__(self, key: str) -> Any:
        if key in self._parameters:
            return self._parameters[key]
        if key in self._aliases:
            return self._parameters[self._aliases[key]]

    def __getattr__(self, key: str) -> Any:
        if key in self._parameters:
            return self._parameters[key]
        if key in self._aliases:
            return self._parameters[self._aliases[key]]

    @property
    def parameters(self) -> dict:
        return self._parameters.copy()

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Parameters):
            return NotImplemented
        return self._parameters == other.parameters

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, Parameters):
            return NotImplemented
        if not set(self._parameters) < set(other.parameters):
            return False
        for k, v in self._parameters.items():
            if v != other.parameters[k]:
                return False
        return True

    def __gt__(self, other: Any) -> bool:
        if not isinstance(other, Parameters):
            return NotImplemented
        if not set(self._parameters) > set(other.parameters):
            return False
        for k, v in other.parameter.items():
            if v != self._parameters[k]:
                return False
        return True

    def __le__(self, other: Any) -> bool:
        return self.__eq__(other) or self.__lt__(other)

    def __ge__(self, other: Any) -> bool:
        return self.__eq__(other) or self.__gt__(other)

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)
