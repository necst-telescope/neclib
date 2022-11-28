__all__ = ["config", "configure"]

import os
import shutil
from collections.abc import ItemsView, KeysView, ValuesView
from pathlib import Path
from typing import Any, Callable, Generic, List, Optional, Tuple, Type, TypeVar, Union

import astropy.units as u
from astropy.coordinates import EarthLocation
from tomlkit.toml_file import TOMLFile

from . import EnvVarName, get_logger
from .exceptions import NECSTConfigurationError
from .utils import ValueRange

logger = get_logger(__name__)

DefaultNECSTRoot = Path.home() / ".necst"
DefaultConfigPath = DefaultNECSTRoot / "config.toml"

T = TypeVar("T")
V = TypeVar("V")


class Parameter(Generic[T, V]):
    def __init__(self, parser: Callable[[T], V]) -> None:
        self._parser = parser

    def __set_name__(self, owner: Type[object], name: str) -> None:
        self._name = name

    @property
    def _private_name(self):
        return "_" + self._name

    def __get__(
        self, obj: object, objtype: Optional[Type[object]] = None
    ) -> Optional[V]:
        if obj is None:
            return None
        return getattr(obj, self._private_name)

    def __set__(self, obj: object, value: T) -> None:
        if type(getattr(obj, self._name, None)) not in [type(None), self.__class__]:
            raise AttributeError(f"Cannot overwrite existing attribute {self._name}")
        parsed = self._parser(value)
        if isinstance(parsed, Path):  # Handle relative path, inside dedicated directory
            parsed = getattr(obj, "_dotnecst", DefaultNECSTRoot) / parsed
        setattr(obj, self._private_name, parsed)


class Configuration:
    """NECST configuration.

    This parameter collection supports flexible name look-up. If you query the parameter
    'antenna' by ``config.antenna``, all parameters prefixed by 'antenna' will be
    extracted.

    Examples
    --------
    >>> neclib.config.observatory
    'OMU1P85M'
    >>> neclib.config.antenna_pid_param_az
    [1.5, 0.0, 0.0]
    >>> neclib.config.antenna_pid_param
    SimpleNamespace(az=[1.5, 0.0, 0.0], el=[1.5, 0.0, 0.0])
    >>> neclib.config.antenna_pid_param.az
    [1.5, 0.0, 0.0]

    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        self._config = None
        self.reload()

    def reload(self) -> None:
        """Reload the parameters, in case the config file is updated.

        Warning
        -------
        Parameters set manually (like `config.<parameter_name> = ...`) will be lost on
        reload.

        """
        self.__config_path = self.__find_config_path()
        params = TOMLFile(self.__config_path).read().unwrap()
        new_config = _Cfg(self, **params)
        # Attribute validation
        attr_cross_section = set(dir(self.__class__)) & set(dir(new_config))
        dupl_attrs = list(filter(lambda x: not x.startswith("_"), attr_cross_section))
        if dupl_attrs:
            raise NECSTConfigurationError(
                f"Parameters {dupl_attrs} cannot be set; reserved name."
            )
        # Assign after validation
        self.__config = new_config

    @property
    def _dotnecst(self) -> Path:
        return self.__config_path.parent

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(file='{self.__config_path}')"

    def __str__(self) -> str:
        return str(self.__config)

    def __getattr__(self, key: str) -> Optional[Any]:
        return getattr(self.__config, key, None)

    def __find_config_path(self) -> Path:
        candidates = [DefaultNECSTRoot]
        if EnvVarName.necst_root in os.environ:
            candidates.insert(0, Path(os.environ[EnvVarName.necst_root]))

        for path in candidates:
            config_path = path if path.is_file() else path / "config.toml"
            if config_path.exists():
                logger.info(f"Imported configuration file '{config_path}'")
                return config_path
        logger.error(
            "Config file not found, using the default parameters. "
            "To create the file with default parameters, run `neclib.configure()`."
        )
        return Path(__file__).parent / "src" / "config.toml"

    @classmethod
    def configure(cls) -> None:
        """Create config file under ``$HOME/.necst``"""
        DefaultNECSTRoot.mkdir(exist_ok=True)
        for filename in ["config.toml", "pointing_param.toml"]:
            _target_path = DefaultNECSTRoot / filename
            if _target_path.exists():
                logger.error(f"'{_target_path}' already exists, skipping...")
                continue
            shutil.copyfile(Path(__file__).parent / "src" / filename, _target_path)
        cls().reload()


class _Cfg:

    observatory = Parameter(str)
    location = Parameter(lambda x: EarthLocation(**x))
    observation_frequency = Parameter(u.Quantity)
    simulator = Parameter(bool)
    record_root = Parameter(Path)
    alert_interval_sec = Parameter(float)
    antenna_pid_param_az = Parameter(list)
    antenna_pid_param_el = Parameter(list)
    antenna_drive_range_az = Parameter(lambda x: ValueRange(*map(u.Quantity, x)))  # type: ignore  # noqa: E501
    antenna_drive_range_el = Parameter(lambda x: ValueRange(*map(u.Quantity, x)))  # type: ignore  # noqa: E501
    antenna_drive_warning_limit_az = Parameter(lambda x: ValueRange(*map(u.Quantity, x)))  # type: ignore  # noqa: E501
    antenna_drive_warning_limit_el = Parameter(lambda x: ValueRange(*map(u.Quantity, x)))  # type: ignore  # noqa: E501
    antenna_drive_critical_limit_az = Parameter(lambda x: ValueRange(*map(u.Quantity, x)))  # type: ignore  # noqa: E501
    antenna_drive_critical_limit_el = Parameter(lambda x: ValueRange(*map(u.Quantity, x)))  # type: ignore  # noqa: E501
    antenna_pointing_accuracy = Parameter(u.Quantity)
    antenna_pointing_parameter_path = Parameter(Path)
    antenna_scan_margin = Parameter(u.Quantity)
    antenna_max_acceleration_az = Parameter(u.Quantity)
    antenna_max_acceleration_el = Parameter(u.Quantity)
    antenna_max_speed_az = Parameter(u.Quantity)
    antenna_max_speed_el = Parameter(u.Quantity)
    antenna_speed_to_pulse_factor_az = Parameter(u.Quantity)
    antenna_speed_to_pulse_factor_el = Parameter(u.Quantity)
    antenna_command_frequency = Parameter(int)
    antenna_command_offset_sec = Parameter(float)
    ros_service_timeout_sec = Parameter(float)
    ros_communication_deadline_sec = Parameter(float)
    ros_logging_interval_sec = Parameter(float)
    ros_topic_scan_interval_sec = Parameter(float)

    def __init__(
        self, config_manager: Configuration, prefix: str = "", /, **kwargs
    ) -> None:
        keys = set(k.lower() for k in kwargs.keys())
        if len(keys) != len(kwargs):
            dupl = set(kwargs) - keys
            raise NECSTConfigurationError(
                f"Parameters {dupl} cannot be assigned; duplicate definition."
            )

        self.__config_manager = config_manager
        self.__prefix = prefix
        self.__parameters = [
            self.__assign_parameter(key, value) for key, value in kwargs.items()
        ]

    def keys(self, full: bool = False) -> KeysView:
        prefix_length = len(self.__prefix)
        if full:
            p = self.__parameters
        else:
            p = map(lambda x: (x[0][prefix_length:], x[1]), self.__parameters)
        return dict(p).keys()

    def values(self) -> ValuesView:
        prefix_length = len(self.__prefix)
        p = map(lambda x: (x[0][prefix_length:], x[1]), self.__parameters)
        return dict(p).values()

    def items(self, full: bool = False) -> ItemsView:
        prefix_length = len(self.__prefix)
        if full:
            p = self.__parameters
        else:
            p = map(lambda x: (x[0][prefix_length:], x[1]), self.__parameters)
        return dict(p).items()

    @property
    def _dotnecst(self) -> Path:
        return self.__config_manager._dotnecst

    @property
    def _prefix(self) -> str:
        return self.__prefix

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(prefix='{self.__prefix}')"

    def __str__(self) -> str:
        width = max(len(p) for p, _ in self.__parameters) - len(self.__prefix) + 2

        def _prettify(key: str) -> str:
            key = key[len(self.__prefix) :]
            value = getattr(self, key, None)
            return f"    {key:{width}s}{value!s}    ({type(value).__name__})"

        _parameters = "\n".join([_prettify(k) for k, _ in self.__parameters])
        return f"NECST configuration (prefix='{self.__prefix}')\n{_parameters}"

    def __assign_parameter(self, k, v) -> Tuple[str, Any]:
        if k.startswith("_"):
            raise NECSTConfigurationError(
                f"Parameter '{k!r}' cannot be assigned; name starts with '_' is invalid"
            )
        k = self.__prefix + k
        if k.lower() in self.__reserved_names:
            raise NECSTConfigurationError(
                f"Parameter {k!r} cannot be assigned; reserved name."
            )
        setattr(self, k, v)
        return (k, getattr(self, k))

    @property
    def __reserved_names(self) -> List[str]:
        return [
            k.lower() for k, v in vars(self).items() if not isinstance(v, Parameter)
        ]

    def __getattr__(self, key: str) -> Optional[Union[Any, "_Cfg"]]:
        if key.startswith("_"):
            raise AttributeError(f"Attribute '{key}' not found.")

        value = None
        if not key.islower():
            value = getattr(self, key.lower(), None)
        if (value is None) and self.__prefix and (not key.startswith(self.__prefix)):
            value = getattr(self, self.__prefix + key, None)
        if value is None:
            prefix = key + "_"
            prefix_length = len(prefix)
            _match = {
                k[prefix_length:]: v
                for k, v in self.__parameters
                if k.lower().startswith(prefix.lower())
            }
            value = _Cfg(self.__config_manager, prefix, **_match) if _match else None

        return value

    def __gt__(self, other: Any) -> bool:
        if other is None:
            return True

        if not isinstance(other, _Cfg):
            return NotImplemented

        if set(self.keys()) <= set(other.keys()):
            return False

        lazy_eq = (getattr(self, k) == getattr(other, k) for k in other.keys())
        full_eq = (getattr(self, k) == getattr(other, k) for k in other.keys(full=True))
        return True if all(lazy_eq) or all(full_eq) else False

    def __lt__(self, other: Any) -> bool:
        if other is None:
            return False

        if not isinstance(other, _Cfg):
            return NotImplemented

        if set(self.keys()) >= set(other.keys()):
            return False

        lazy_eq = (getattr(self, k) == getattr(other, k) for k in self.keys())
        full_eq = (getattr(self, k) == getattr(other, k) for k in self.keys(full=True))
        return True if all(lazy_eq) or all(full_eq) else False

    def __eq__(self, other: Any) -> bool:
        if other is None:
            return False

        if not isinstance(other, _Cfg):
            return NotImplemented

        if set(self.keys()) != set(other.keys()):
            return False

        lazy_eq = (getattr(self, k) == getattr(other, k) for k in self.keys())
        full_eq = (getattr(self, k) == getattr(other, k) for k in self.keys(full=True))
        return True if all(lazy_eq) or all(full_eq) else False

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def __ge__(self, other: Any) -> bool:
        return self.__eq__(other) or self.__gt__(other)

    def __le__(self, other: Any) -> bool:
        return self.__eq__(other) or self.__lt__(other)


config = Configuration()
configure = Configuration.configure
