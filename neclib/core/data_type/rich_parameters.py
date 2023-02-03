import os
import re
import warnings
from dataclasses import dataclass
from typing import IO, Any, Callable, Dict, Generic, Tuple, TypeVar, Union

from tomlkit.container import Container
from tomlkit.items import Item

from ..exceptions import NECSTAccessibilityWarning, NECSTParameterNameError
from ..files import toml
from ..formatting.dict_to_html import html_repr_of_dict
from .parameters import Parameters

T_value = TypeVar("T_value")


@dataclass
class _RichParameter(Generic[T_value]):
    key: str
    value: T_value

    @property
    def parsed(self) -> Any:
        """Value which may be converted by attached parser."""
        if not hasattr(self, "_parsed_value"):
            _value = self.value
            if isinstance(_value, (Container, Item)):
                _value = _value.unwrap()
            self._parsed_value = self.parser(_value)
        return self._parsed_value

    @property
    def parser(self) -> Callable[[T_value], Any]:
        """Parser to convert value to another type or modify the value."""
        return self._parser if hasattr(self, "_parser") else lambda x: x

    @parser.setter
    def parser(self, __parser: Callable[[T_value], Any]) -> None:
        if hasattr(self, "_parsed_value"):
            del self._parsed_value
        self._parser = __parser

    def __str__(self) -> str:
        return str(self.parsed)


class RichParameters(Parameters):
    """Parameters with flexible look-up and high-level representation support.

    Parameters are not always just a key-value pair. Sometimes, we need higher level
    representation; all-in-one object that has rich information and methods about the
    parameter. This class provides a way to store such parameters.

    Parameters
    ----------
    __prefix
        Internally used prefix, which enables name-based filtering of parameters.
    **kwargs
        Parameters to be stored.

    Examples
    --------
    >>> params = RichParameters(a=1, b=2, **{"c[deg]": 3})

    You can attach a parser to a parameter, which will be used to convert the value to
    another high-level representation or modify the value.

    >>> params.attach_parser(b=lambda x: x * 2 * u.m)
    >>> params.b
    <Quantity 4. m>

    You can filter parameters by name, using the parameter prefix to accessing the
    attribute.

    >>> params = RichParameters(
    ...     general_param1=1,
    ...     specific_param1=2,
    ...     **{"general_param2[deg]": 3}
    ... )
    >>> params.general
    RichParameters
    general_param1 = 1 (_RichParameter)
    general_param2 = 3d00m00s (_RichParameter)

    """

    __slots__ = ("_prefix",)

    _unit_matcher = re.compile(r"([\w\.]*)\[([\w/\s\*\^-]*)\]")

    def __init__(self, __prefix: str = "", /, **kwargs: Any) -> None:
        self._prefix = __prefix
        params = {k: _RichParameter(k, v) for k, v in kwargs.items()}
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=NECSTAccessibilityWarning)
            super().__init__(**params)
        self._parameters: Dict[str, _RichParameter[Any]]
        aliases = {k.replace(".", "_"): k for k in self._parameters.keys() if "." in k}
        self.attach_aliases(**aliases)

    @classmethod
    def from_file(cls, file: Union[os.PathLike, str, IO], /):
        """Read parameters from a TOML file.

        Parameters
        ----------
        file
            The file path or file object.

        Examples
        --------
        >>> params = RichParameters.from_file("path/to/file.toml")

        You can also read parameters from a file-like object.

        >>> with open("path/to/file.toml") as f:
        ...     params = RichParameters.from_file(f)

        And if you wish, remote files can be read:

        >>> params = RichParameters.from_file("https://example.com/file.toml")

        """
        file_path = isinstance(file, (os.PathLike, str))
        _params = toml.read(file)
        params = toml.flatten(_params)

        inst = cls(**params)
        if file_path:
            inst._path = file
        return inst

    def _parse(self, k: str, v: _RichParameter) -> Tuple[str, _RichParameter]:
        parsed_k, parsed_v = super()._parse(k, v.value)
        v.key = parsed_k
        v.value = parsed_v
        return parsed_k, v

    def attach_parsers(self, **kwargs: Callable[[Any], Any]) -> None:
        """Attach parsers to parameters.

        Parameters
        ----------
        **kwargs
            Parsers to be attached to parameters.

        Raises
        ------
        NECSTParameterNameError
            No parameter with the given name (key of the ``kwargs``) exists.

        Examples
        --------
        >>> params = RichParameters(a=1, b=2, **{"c[deg]": 3})
        >>> params.attach_parsers(b=lambda x: x * 2 * u.m)
        >>> params.b
        <Quantity 4. m>

        """
        for k, v in kwargs.items():
            if k in self._parameters:
                self._parameters[k].parser = v
            elif k in self._aliases:
                self._parameters[self._aliases[k]].parser = v

            try:
                self._pick(k).parser = v
            except KeyError:
                raise NECSTParameterNameError(f"Unknown parameter: {k!r}")

    def get(self, key: str, /) -> Any:
        """Flexibly look-up the parameters.

        Implementation of the ``__getitem__`` and ``__getattr__`` special methods.

        Parameters
        ----------
        key
            The name of the parameter.

        """
        try:
            return self._pick(key).parsed
        except KeyError:
            filtered = self._filter(key)

        if filtered:
            prefix = self._prefix + "_" + key if self._prefix else key
            inst = self.__class__(prefix, **filtered)
            inst._path = self._path
            for k, v in self._aliases.items():
                if v in filtered:
                    inst._aliases[k] = v
            for k, v in filtered.items():
                inst._parameters[k].parser = self._parameters[k].parser
            return inst
        raise KeyError(key)

    def __getitem__(self, key: str, /) -> Any:
        return self.get(key)

    def __getattr__(self, key: str, /) -> Any:
        try:
            return self.get(key)
        except KeyError as e:
            # Should raise AttributeError to deny permissiveness to nonexistent
            # attributes. If an object performs as if it has any attributes by not
            # raising AttributeError, Jupyter Notebook won't trust the result of
            # `hasattr(obj, "_repr_html_")` hence don't display rich representations.
            # See also: https://github.com/jupyter/notebook/issues/2014
            raise AttributeError(f"No attribute {key!r}") from e

    def _filter(self, key: str, /) -> Dict[str, Any]:
        """Extract parameters which key starts with given key."""
        extracted = {}
        qualkey = self._prefix + "_" + key if self._prefix else key
        for k, v in self._parameters.items():
            if self._match(v.key, qualkey):
                extracted[k] = v.value
        for k, v in self._aliases.items():
            if self._match(k, qualkey):
                extracted[v] = self._parameters[v].value
        return extracted

    def _pick(self, key: str, /) -> Any:
        """Pick-up at most one parameter, which key exactly matches to given one."""
        qualkey = self._prefix + "_" + key if self._prefix else key
        for v in self._parameters.values():
            if self._match(qualkey, v.key, strict=True):
                return v
        for k, v in self._aliases.items():
            if self._match(qualkey, k, strict=True):
                return self._parameters[v]
        raise KeyError(key)

    def _normalize(self, qualkey: str, /) -> str:
        """Normalize the key to enable structure insensitive access.

        Parameters
        ----------
        qualkey
            The key to be normalized. It should be a qualified key, i.e. the key with
            the prefix.

        """
        return qualkey.replace(".", "_")

    def _match(self, k1: str, k2: str, /, *, strict: bool = False) -> bool:
        """Judge whether namespace ``k1`` contains key ``k2``."""
        if strict:
            return self._normalize(k1) == self._normalize(k2)
        return self._normalize(k1).startswith(self._normalize(k2))

    def _repr_html_(self) -> str:
        """Rich representation for Jupyter Notebook."""
        return html_repr_of_dict(
            {k: v.parsed for k, v in self._parameters.items()},
            type(self),
            aliases=self._aliases,
            metadata={"File": self._path, "Prefix": self._prefix},
        )
