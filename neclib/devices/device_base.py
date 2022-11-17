from abc import ABC, abstractmethod
from typing import Any, Dict, Final, Optional, Type, final

from .. import ConfigurationError, utils
from ..configuration import _Cfg, Configuration, config


class _CfgManager:
    def __set_name__(self, owner: Type[object], name: str) -> None:
        self.name = "_" + name

    def __get__(self, instance: object, type: Optional[Type[object]] = None):
        if instance is None:
            return None
        return getattr(instance, self.name, None)

    def __set__(self, instance: object, value: Any) -> None:
        if not isinstance(value, _Cfg):
            raise TypeError("Configuration object expected.")

        current_config = getattr(instance, self.name, None)

        if current_config < value:
            # If new configuration is the superset of currently assigned one, update it.
            setattr(instance, self.name, value)
        elif (current_config is None) and (value is None):
            pass
        elif current_config >= value:
            pass
        else:
            raise ConfigurationError(
                "Currently this software doesn't support merging multiple config "
                "objects. Please include all configurations for single device in single"
                " config object (others should contain subset of that; notably the "
                "identifier) or make identical config objects for all aliases."
            )


class DeviceBase(ABC):
    """Base class for all devices.

    Parameters
    ----------
    config
        Device configuration, as ``Configuration`` group object.
    key
        Identifier to uniquely specify single device.

    """

    _instances: Final[Dict[str, Any]] = {}
    conf: Configuration

    Manufacturer: str = ""
    Model: str

    Identifier: Optional[str] = None
    Config = _CfgManager()

    @final
    def __new__(cls):
        if cls.Identifier is None:
            return super().__new__(cls)

        _cfg = getattr(config, utils.to_snake_case(cls.__name__))

        identifier = (
            "" if cls.Identifier is None else getattr(_cfg, cls.Identifier, None)
        )
        key = f"{cls.Model}_{cls.Manufacturer}_{identifier}"
        if key not in cls._instances:
            cls._instances[key] = super().__new__(cls)

        cls._instances[key].Config = _cfg
        return cls._instances[key]

    @final
    def __repr__(self) -> str:
        model = f"model={self.Model!r}"
        manufacturer = f"manufacturer={self.Manufacturer!r}"
        ident = ""
        if self.Identifier is not None:
            ident = f"{self.Identifier}={getattr(self.Config, self.Identifier, None)}"
        return f"{self.__class__.__name__}({model}, {manufacturer}, {ident})"

    @final
    def __str__(self) -> str:
        return self.__repr__()

    @abstractmethod
    def finalize(self) -> None:
        """Safely shut down the device.

        This method should always be called on quitting the program.

        """
        ...
