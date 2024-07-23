from abc import ABC, abstractmethod
from collections import UserDict
from typing import (
    Any,
    ClassVar,
    Dict,
    Generic,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    final,
    overload,
)

from .. import config, utils
from ..core import Parameters
from ..core.configuration import Configuration
from ..core.normalization import partial


def get_device_configuration():
    return {k[:-2]: v for k, v in config.items() if k.endswith("._")}


class DeviceBase(ABC):

    Model: ClassVar[str]
    Manufacturer: ClassVar[str]
    Identifier: ClassVar[Optional[str]] = None
    is_simulator: ClassVar[bool] = False

    Config: ClassVar[Union[Configuration, None]] = None

    _instances: ClassVar[Dict[Any, "DeviceBase"]]
    _initialized: ClassVar[bool] = False
    _implementations: List[Type["DeviceBase"]] = []
    _is_autogenerated: ClassVar[bool] = False
    _kind: ClassVar[Type["DeviceBase"]]

    def __init_subclass__(cls) -> None:
        if hasattr(cls, "Model") and (not cls._is_autogenerated):
            # `cls.__subclasses__()` returns its immediate subclasses only, and they
            # should be device kind definition, not controller implementations for each
            # model. This (`cls._implementations`) is similar to that, but this includes
            # grandchild classes, and not includes abstract classes (no `cls.Model` is
            # set).
            cls._implementations.append(cls)
            if not hasattr(cls, "_instances"):
                setattr(cls, "_instances", {})
        if cls.__base__ is DeviceBase:
            cls._kind = cls

    def __new__(cls) -> "DeviceBase":
        if (cls is DeviceBase) or (not hasattr(cls, "Model")):
            # Ensure no instantiation of ABC, to avoid unintended class variable change.
            raise TypeError

        # Singleton check.
        identity = cls._identity(cls.Config, cls.Identifier)
        if identity not in cls._instances:
            inst = super().__new__(cls)
            cls._instances[identity] = inst

        # Initialization status check.
        if cls._initialized:
            cls.__init__ = lambda *args, **kwargs: None
        cls._initialized = True

        return cls._instances[identity]

    @classmethod
    def get_simulator_class(cls) -> Type["DeviceBase"]:
        if cls.is_simulator:
            return cls
        same_kind = cls._kind.__subclasses__()
        simulator = [c for c in same_kind if c.is_simulator]
        if len(simulator) == 0:
            raise NotImplementedError(
                f"No simulator implementation for {cls.__name__} "
                f"({cls._kind.__name__}) is found."
            )
        return simulator[0]

    @staticmethod
    def _normalize(key: str, /) -> str:
        return key.replace("_", "").lower()

    @classmethod
    def _find_config(
        cls, name: str, identifier: Optional[str] = None
    ) -> Optional[Configuration]:
        this_device_config = config[name]
        model = cls._normalize(this_device_config._)  # type: ignore
        identity = None
        if identifier is not None:
            identity = getattr(this_device_config, identifier, None)

        device_configuration = get_device_configuration()
        model_filtered = [
            k for k, v in device_configuration.items() if cls._normalize(v) == model
        ]
        _cfgs: List[Configuration] = [config[k] for k in model_filtered]  # type: ignore
        cfg = None
        for _cfg in _cfgs:
            if (identifier is None) or (getattr(_cfg, identifier, None) == identity):
                cfg += _cfg

        return cfg

    @staticmethod
    def _identity(
        cfg: Union[Configuration, None], identifier: Optional[str] = None
    ) -> Any:
        if identifier is None:
            return None
        identity = getattr(cfg, identifier, None)
        if isinstance(identity, Parameters):
            return None
        return identity

    @overload
    @classmethod
    def bind(cls, name: str, model: str) -> Type["DeviceBase"]: ...

    @overload
    @classmethod
    def bind(
        cls, name: str, model: Dict[str, str]
    ) -> "Devices[str, Type[DeviceBase]]": ...

    @final
    @classmethod
    def bind(
        cls, name: str, model: Union[str, Dict[str, str]]
    ) -> Union[Type["DeviceBase"], "Devices[str, Type[DeviceBase]]"]:
        impl = {cls._normalize(_impl.Model): _impl for _impl in cls._implementations}
        if isinstance(model, dict):
            bound_devices = {
                key: cls.bind(f"{name}.{key}", _model) for key, _model in model.items()
            }
            return Devices(bound_devices)
        else:
            model_impl = impl[cls._normalize(model)]
            if config.simulator:
                try:
                    simulator = model_impl.get_simulator_class()
                    simulator.Identifier = model_impl.Identifier
                    model_impl = simulator
                except NotImplementedError:
                    pass
            Name = ".".join([utils.toCamelCase(n) for n in name.split(".")])
            cfg = cls._find_config(name, model_impl.Identifier)
            identity = cls._identity(cfg, model_impl.Identifier)
            if identity in model_impl._instances:
                return model_impl._instances[identity].__class__
            return type(
                Name,
                (model_impl,),
                dict(Config=cfg, __module__=cls.__module__, _is_autogenerated=True),
            )

    def __repr__(self) -> str:
        model = f"model={self.Model}"
        manufacturer = f"manufacturer={self.Manufacturer}"
        identity = "<no device identity defined>"
        if self.Identifier:
            _id = getattr(self.Config, self.Identifier, None)
            identity = f"{self.Identifier}={_id!r}"
        metadata = ", ".join([model, manufacturer, identity])
        return f"{self.__class__.__name__}({metadata})"

    __str__ = __repr__

    @abstractmethod
    def finalize(self) -> None: ...


T_key = TypeVar("T_key")
T_value = TypeVar("T_value")


class Devices(UserDict, Generic[T_key, T_value]):
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({super().__repr__()})"

    __str__ = __repr__

    def __init__(
        self,
        anonymous_device: Optional[
            Union[
                DeviceBase,
                Type[DeviceBase],
                Dict[str, DeviceBase],
                Dict[str, Type[DeviceBase]],
            ]
        ] = None,
        /,
        **named_devices: Union[DeviceBase, Type[DeviceBase]],
    ) -> None:
        super().__init__()

        if (anonymous_device is not None) and (len(named_devices) > 0):
            raise ValueError("Cannot specify both anonymous and named devices")

        if anonymous_device is None:
            self.update(named_devices)
        elif isinstance(anonymous_device, dict):
            # Keep compatibility with `dict` constructor's signature;
            # `__init__(__map, /, **kwargs) -> None`
            self.update(anonymous_device)
        else:
            self.update({None: anonymous_device})

    @property
    def _is_single_anonymous_device(self) -> bool:
        return (len(self) == 1) and (list(self.keys())[0] is None)

    def _parse_id_query(
        self, id: Optional[str] = None
    ) -> Tuple[Union[None, str], Union[None, str]]:
        if id is None:
            return (None, None)
        if self._is_single_anonymous_device:
            # Anonymous device doesn't have device-ID by definition
            return (None, id)
        if id.find(".") != -1:
            # Dot-separated value is parsed to `<device-ID>.<channel-ID>`
            return tuple(id.rsplit(".", 1))
        # Device-ID takes precedence when given `id` doesn't match certain pattern
        return (id, None)

    @overload
    def __call__(self, *args, id: str, **kwargs) -> DeviceBase: ...

    @overload
    def __call__(self, *args, **kwargs) -> "Devices": ...

    def __call__(self, *args, **kwargs) -> Union[DeviceBase, "Devices"]:
        """Emulate initialization of attached device controllers."""
        device_id, channel_id = self._parse_id_query(kwargs.get("id", None))
        if (device_id is None) and (channel_id is None):
            return Devices({k: v(*args, **kwargs) for k, v in self.items()})
        kwargs["id"] = channel_id
        return self[device_id](*args, **kwargs)

    def __getattr__(self, key: str, /) -> Any:
        """Emulate attribute access to attached device controllers."""
        targets = {k: getattr(v, key) for k, v in self.items()}
        if all(callable(t) for t in targets.values()):

            def func(*args, **kwargs) -> Union[Any, Dict[Union[str, None], Any]]:
                device_id, channel_id = self._parse_id_query(kwargs.get("id", None))
                if (device_id is None) and (channel_id is None):
                    if self._is_single_anonymous_device:
                        return targets[None](*args, **kwargs)
                    return {k: t(*args, **kwargs) for k, t in targets.items()}
                kwargs["id"] = channel_id
                return targets[device_id](*args, **kwargs)

            return func

        elif self._is_single_anonymous_device:
            return targets[None]
        else:
            return targets

    def __getitem__(self, key: Union[str, None], /) -> Any:
        try:
            return super().__getitem__(key)
        except KeyError:
            pass

        if isinstance(key, str):
            item_normalized = {
                k.replace("_", "").lower() if isinstance(k, str) else k: v
                for k, v in self.items()
            }
            _key = key.replace("_", "").lower()
            if _key in item_normalized:
                return item_normalized[_key]

            device_id, channel_id = self._parse_id_query(_key)
            if device_id in item_normalized:
                item = item_normalized[device_id]
                for attr_name in dir(item):
                    attr = getattr(item, attr_name, None)
                    if attr is None:
                        continue
                    try:
                        modified = partial(attr, kwargs={"id": channel_id})
                        print(attr_name, modified)
                        object.__setattr__(item, attr_name, modified)
                    except TypeError as e:
                        print(attr_name, e)
                        continue
                return item

            raise KeyError(channel_id)

        raise KeyError(key)
