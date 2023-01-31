import os
import re
import warnings
from dataclasses import dataclass
from typing import IO, Any, Callable, Dict, Generic, Tuple, TypeVar, Union

from tomlkit.container import Container
from tomlkit.items import Item

from ..exceptions import NECSTAccessibilityWarning, NECSTParameterNameError
from ..files import toml
from .formatting import html_repr_of_dict
from .parameters import Parameters

T_value = TypeVar("T_value")


@dataclass
class _RichParameter(Generic[T_value]):
    key: str
    value: T_value

    @property
    def parsed(self) -> Any:
        if not hasattr(self, "_parsed_value"):
            _value = self.value
            if isinstance(_value, (Container, Item)):
                _value = _value.unwrap()
            self._parsed_value = self.parser(_value)
        return self._parsed_value

    @property
    def parser(self) -> Callable[[T_value], Any]:
        return self._parser if hasattr(self, "_parser") else lambda x: x

    @parser.setter
    def parser(self, __parser: Callable[[T_value], Any]) -> None:
        if hasattr(self, "_parsed_value"):
            del self._parsed_value
        self._parser = __parser

    def __str__(self) -> str:
        return str(self.parsed)


class RichParameters(Parameters):
    """Parameters with arbitrary type support.

    ...

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
        try:
            return self._pick(key).parsed
        except KeyError:
            filtered = self._filter(key)

        if filtered:
            prefix = self._prefix + "_" + key if self._prefix else key
            inst = RichParameters(prefix, **filtered)
            inst._path = self._path
            for k, v in self._aliases.items():
                if v in filtered:
                    inst._aliases[k] = v
            for k, v in filtered.items():
                inst._parameters[k].parser = self._parameters[k].parser
            return inst
        raise KeyError(key)

    def __getitem__(self, key: str) -> Any:
        return self.get(key)

    def __getattr__(self, key: str) -> Any:
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
        qualkey = self._prefix + "_" + key if self._prefix else key
        for v in self._parameters.values():
            if self._match(qualkey, v.key, strict=True):
                return v
        for k, v in self._aliases.items():
            if self._match(qualkey, k, strict=True):
                return self._parameters[v]
        raise KeyError(key)

    def _normalize(self, qualkey: str, /) -> str:
        return qualkey.replace(".", "_")

    def _match(self, k1: str, k2: str, /, *, strict: bool = False) -> bool:
        if strict:
            return self._normalize(k1) == self._normalize(k2)
        return self._normalize(k1).startswith(self._normalize(k2))

    def _repr_html_(self) -> str:
        return html_repr_of_dict(
            {k: v.parsed for k, v in self._parameters.items()},
            type(self),
            aliases=self._aliases,
            metadata={"File": self._path, "Prefix": self._prefix},
        )


RichParameters.from_file("./neclib/src/config.toml")
