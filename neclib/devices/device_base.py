from abc import ABC, abstractmethod
from collections import UserDict
from functools import partial
from typing import Any, ClassVar, Dict, List, Optional, Union, final

from ..configuration import Configuration, _Cfg, config


def get_device_list() -> Dict[str, "DeviceBase"]:
    # Unlike __mro__, __subclasses__ returns immediate subclasses only.
    device_kinds = DeviceBase.__subclasses__()
    table = {}
    for v in device_kinds:
        for impl in v.__subclasses__():
            table[impl.Model.lower()] = impl
    return table


def find_config(
    key: str, identifier: Optional[str] = None
) -> Union[Configuration, _Cfg]:
    if identifier is None:
        return config[key]
    devices = {k[:-3]: v for k, v in config.items() if k.endswith("::_")}
    same_model = {k: config[k] for k in devices if config[k]._ == config[key]._}
    same_machine = {
        k: v
        for k, v in same_model.items()
        if config[k][identifier] == config[key][identifier]
    }
    cfg = None
    for _cfg in same_machine.values():
        cfg += _cfg
    return cfg


class DeviceMapping(UserDict):
    def __getattr__(self, key: str) -> Any:
        targets = [getattr(v, key) for v in self.values()]
        if all(callable(t) for t in targets):

            def func(*args, **kwargs) -> List[Any]:
                return [t(*args, **kwargs) for t in targets]

            return func
        else:
            return targets

    def __call__(self, *args, **kwargs) -> List[Any]:
        return DeviceMapping((k, v(*args, **kwargs)) for k, v in self.items())

    def __repr__(self) -> str:
        items = ", ".join([f"{k}={v!r}" for k, v in self.items()])
        return f"DeviceMapping({items})"


class ConfigManager:
    def __set_name__(self, owner, name):
        self.name = "_" + name

    def __get__(self, instance, owner):
        return getattr(instance, self.name)

    def __set__(self, instance, value):
        setattr(instance, self.name, value)


class DeviceBase(ABC):

    _instances: Dict[str, "DeviceBase"] = {}
    Identifier: Optional[str] = None
    Config: ConfigManager()

    Manufacturer: ClassVar[str] = ""
    Model: ClassVar[str]

    @final
    def __new__(
        cls,
        *,
        name: Optional[str] = None,
        model: Optional[Union[str, Dict[str, str]]] = None,
    ):
        if cls is not DeviceBase:
            if name is None:
                raise ValueError("Name for this device must be specified")
            cfg = find_config(name, cls.Identifier)
            key = (
                f"{cls.Manufacturer}::{cls.Model}::{getattr(cfg, cls.Identifier, None)}"
            )
            if key in cls._instances:
                cls._instances[key].__init__ = lambda *args, **kwargs: None
                return cls._instances[key]

            cls._instances[key] = super().__new__(cls)
            cls._instances[key].Config = cfg
            return cls._instances[key]

        impl = get_device_list()

        if isinstance(model, dict):
            name = {k: f"{name}::{k}" for k in model}
            parsed = {
                k: partial(impl[v.lower()], name=name[k]) for k, v in model.items()
            }
            return DeviceMapping(parsed)

        parsed = partial(impl[model.lower()], name=name)
        return parsed

    @final
    def __repr__(self) -> str:
        model = f"model={self.Model!r}"
        manufacturer = f"manufacturer={self.Manufacturer!r}"
        ident = ""
        if self.Identifier is not None:
            ident = f"{self.Identifier}={getattr(self.Config, self.Identifier, None)!r}"
        return f"{self.__class__.__name__}({model}, {manufacturer}, {ident})"

    @final
    def __str__(self) -> str:
        return self.__repr__()

    @abstractmethod
    def finalize(self) -> None:
        ...
