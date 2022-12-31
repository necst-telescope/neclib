from abc import ABC, abstractmethod
from collections import UserDict
from collections.abc import KeysView
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
    devices = {k[:-2]: v for k, v in config.items() if k.endswith("._")}
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
    def __getattr__(self, key: str) -> Dict[str, Any]:
        targets = {k: getattr(v, key) for k, v in self.items()}
        if all(callable(t) for t in targets.values()):

            def func(*args, **kwargs) -> List[Any]:
                if (
                    ("id" in kwargs)
                    and isinstance(kwargs["id"], str)
                    and (len(kwargs["id"].split(".")) == 2)
                ):
                    device_id, ch_id = kwargs["id"].split(".")
                    kwargs["id"] = ch_id
                    return targets[device_id](*args, **kwargs)
                return {k: t(*args, **kwargs) for k, t in targets.items()}

            return func
        else:
            return targets

    def __call__(self, *args, **kwargs) -> "DeviceMapping[str, Any]":
        if (
            ("id" in kwargs)
            and isinstance(kwargs["id"], str)
            and (len(kwargs["id"].split(".")) == 2)
        ):
            device_id, ch_id = kwargs["id"].split(".")
            kwargs["id"] = ch_id
            return self[device_id](*args, **kwargs)
        return DeviceMapping((k, v(*args, **kwargs)) for k, v in self.items())

    def __repr__(self) -> str:
        items = ", ".join([f"{k}={v!r}" for k, v in self.items()])
        return f"DeviceMapping({items})"

    def __str__(self) -> str:
        items = ", ".join([f"{k}={v!s}" for k, v in self.items()])
        return f"DeviceMapping({items})"

    def keys(self) -> KeysView:
        _all = {}
        for devname, dev in super().items():
            channels = dev.keys()
            if len(channels) > 0:
                for ch in channels:
                    _all[f"{devname}.{ch}"] = None
            else:
                _all[devname] = None
        return _all.keys()


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
            key = f"{cls.Manufacturer}.{cls.Model}.{getattr(cfg, cls.Identifier, None)}"
            if key in cls._instances:
                cls._instances[key].__init__ = lambda *args, **kwargs: None
                return cls._instances[key]

            cls._instances[key] = super().__new__(cls)
            cls._instances[key].Config = cfg
            return cls._instances[key]

        impl = get_device_list()

        if isinstance(model, dict):
            name = {k: f"{name}.{k}" for k in model}
            parsed = {
                k: partial(impl[v.lower()], name=name[k]) for k, v in model.items()
            }
            return DeviceMapping(parsed)

        parsed = partial(impl[model.lower()], name=name)
        return parsed

    @final
    def __getitem__(self, key: str) -> "DeviceBase":
        # TODO: This should return collection of `partial` methods or its effective
        # equivalents, with `id` arguments set like `DeviceMapping` does.
        raise NotImplementedError

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

    @final
    def keys(self) -> KeysView:
        return getattr(self.Config, "channel", {}).keys()
