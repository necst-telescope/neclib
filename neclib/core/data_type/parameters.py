"""Interface to access NECLIB parameters.

This module defines the NECLIB standard parameter interface. The values can be any
Python built-in type, or physical quantity which need units specified.

The parameters would be stored in TOML files, in the following format:

.. code-block:: toml

   [parameter_kind]
   parameter_name = value

   [another_parameter_kind]
   "parameter_with_units[units]" = value
   parameter_without_units = value

The parameters should be grouped by their kind, which is specified by the TOML table
name. This kind won't be kept in the parameter interface, but we require its use to
keep the parameter files readable.

"""

import os
import re
import warnings
from itertools import chain
from typing import IO, Any, Dict, List, Tuple, Union

import astropy.units as u
from astropy.coordinates import Angle

from ..exceptions import NECSTAccessibilityWarning, NECSTParameterNameError
from ..files import toml
from ..formatting.dict_to_html import html_repr_of_dict


class Parameters:
    """General format of NECLIB parameters.

    This class provides a convenient interface to access the parameters, whose values
    can be physical quantities; which contain units. The parameters can be stored in
    TOML files, so this class also provides a its parser.

    Examples
    --------
    If the parameters are stored in a TOML file, use ``from_file`` method:

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

    And you can convert the units on class initialization:

    >>> params = Parameters(**{"distance[pc]": "10m")
    >>> params["distance"]
    <Quantity 3.24077929e-16 pc>

    You can also access the parameters as attributes:

    >>> params.distance
    <Quantity 10. pc>

    Notes
    -----
    The units are parsed using ``astropy.units`` and ``astropy.coordinates.Angle``. The
    units are parsed from the parameter name, so the parameter name must be in the
    following format: ``parameter_name[unit]``.

    """

    __slots__ = ("_parameters", "_metadata", "_aliases")

    _unit_matcher = re.compile(r"(\w*)\[([\w/\s\*\^-]*)\]")
    # Matches `key[unit]` format. Key should be composed of alphanumeric characters
    # and/or underscores. Unit can be composed of alphanumeric characters, whitespaces
    # and `*/^-`.

    _angle_units: List[str] = [unit.name for unit in u.rad.find_equivalent_units()] + [
        alias for unit in u.rad.find_equivalent_units() for alias in unit.aliases
    ]

    def __init__(self, **kwargs) -> None:
        self._parameters = dict(map(self._parse, kwargs.keys(), kwargs.values()))
        self._metadata = {}
        self._aliases: Dict[str, str] = {}

    @classmethod
    def from_file(cls, file: Union[os.PathLike, str, IO], /):
        """Read parameters from a TOML file.

        Parameters
        ----------
        file
            The file path or file object.

        """
        file_path = isinstance(file, (os.PathLike, str))
        params = toml.read(file)
        params = {k: v for x in params.unwrap().values() for k, v in x.items()}

        inst = cls(**params)
        if file_path:
            inst._metadata["path"] = file
        return inst

    def attach_aliases(self, **kwargs: str) -> None:
        """Attach aliases to the parameters.

        Different names can be used to access the same parameter. This is useful when
        the parameter name is too long, or when the parameter name has some dialects.

        Parameters
        ----------
        **kwargs
            The aliases to attach. The keys are the alias names, and the values are the
            existing parameter names.

        """
        for k, v in kwargs.items():
            self._validate(k)
            if v not in self._parameters:
                raise NECSTParameterNameError(f"Unknown parameter: {v!r}")
            if k in self._parameters:
                raise NECSTParameterNameError(
                    f"Cannot create alias with existing parameter name: {k!r}"
                )
            if k not in self._aliases:
                self._aliases[k] = v

    def __str__(self) -> str:
        width = max(len(x) for x in self._parameters)
        params = [
            f"{k:{width}s} = {v} ({type(v).__name__})"
            for k, v in self._parameters.items()
        ]
        return self.__class__.__name__ + "\n" + "\n".join(params)

    def __repr__(self) -> str:
        return self.__class__.__name__ + f"({len(self._parameters)} elements)"

    def _repr_html_(self) -> str:
        return html_repr_of_dict(
            self._parameters,
            type(self),
            aliases=self._aliases,
            metadata=self._metadata,
        )

    def _validate(self, key: str, /) -> None:
        """Check the parameter name is not reserved.

        Reserved names are `__slots__` contents (possible instance variables) and
        `__class__.__dict__` contents (class variables, including method names).

        Parameters
        ----------
        key
            The parameter name to check.

        """
        slots = chain.from_iterable(
            getattr(cls, "__slots__", []) for cls in self.__class__.__mro__
        )
        if (key in self.__class__.__dict__) or (key in slots):
            raise NECSTParameterNameError(f"Reserved name: {key!r}")
        if not key.isidentifier():
            warnings.warn(
                f"{key!r} isn't a valid Python identifier, "
                "so attribute access isn't available.",
                NECSTAccessibilityWarning,
            )

    def _parse(self, k: str, v: Any, /) -> Tuple[str, Any]:
        if v == {}:
            # Use empty mapping as empty value. This rule is not compliant with TOML
            # spec, but we need a valid TOML value which represents empty.
            v = None

        unit_match = self._unit_matcher.match(k)
        if unit_match is None:
            # When no unit is specified, the value is used as is.
            self._validate(k)
            return k, v

        key, unit = unit_match.groups()
        self._validate(key)
        if v is None:
            return key, v
        if unit in self._angle_units:
            return key, Angle(v, unit=unit)
        return key, u.Quantity(v, unit=unit)

    def __getitem__(self, key: str, /) -> Any:
        if key in self._parameters:
            return self._parameters[key]
        if key in self._aliases:
            return self._parameters[self._aliases[key]]

    def __getattr__(self, key: str, /) -> Any:
        if key in self._parameters:
            return self._parameters[key]
        if key in self._aliases:
            return self._parameters[self._aliases[key]]

    @property
    def parameters(self) -> Dict[str, Any]:
        """Return a copy of the raw parameters."""
        return self._parameters.copy()

    def __eq__(self, other: Any, /) -> bool:
        if not isinstance(other, Parameters):
            return NotImplemented
        return self._parameters == other._parameters

    def __lt__(self, other: Any, /) -> bool:
        if not isinstance(other, Parameters):
            return NotImplemented
        if not set(self._parameters) < set(other._parameters):
            return False
        for k, v in self._parameters.items():
            if v != other._parameters[k]:
                return False
        return True

    def __gt__(self, other: Any, /) -> bool:
        if not isinstance(other, Parameters):
            return NotImplemented
        if not set(self._parameters) > set(other._parameters):
            return False
        for k, v in other._parameters.items():
            if v != self._parameters[k]:
                return False
        return True

    def __le__(self, other: Any, /) -> bool:
        eq, lt = self.__eq__(other), self.__lt__(other)
        if (eq is NotImplemented) or (lt is NotImplemented):
            return NotImplemented
        return eq or lt

    def __ge__(self, other: Any, /) -> bool:
        eq, gt = self.__eq__(other), self.__gt__(other)
        if (eq is NotImplemented) or (gt is NotImplemented):
            return NotImplemented
        return eq or gt

    def __ne__(self, other: Any, /) -> bool:
        eq = self.__eq__(other)
        return NotImplemented if eq is NotImplemented else not self.__eq__(other)
