import os
import shutil
from collections.abc import ItemsView, KeysView, ValuesView
from pathlib import Path
from typing import Any, Dict, Generator, Tuple

import tomlkit
from astropy.coordinates import EarthLocation
from astropy.units import Quantity
from tomlkit.items import Table
from tomlkit.toml_document import TOMLDocument

from . import EnvVarName, get_logger
from .exceptions import NECSTConfigurationError
from .utils import ValueRange, read_file

logger = get_logger(__name__)

DefaultNECSTRoot = Path.home() / ".necst"


class _Parsers:
    observatory = str
    location = lambda x: EarthLocation(**x)  # noqa: E731
    observation_frequency = Quantity
    simulator = bool
    alert_interval_sec = float
    antenna_pid_param_az = list
    antenna_pid_param_el = list
    antenna_drive_range_az = lambda x: ValueRange(*map(Quantity, x))  # noqa: E731
    antenna_drive_range_el = lambda x: ValueRange(*map(Quantity, x))  # noqa: E731
    antenna_drive_warning_limit_az = lambda x: ValueRange(  # noqa: E731
        *map(Quantity, x)
    )
    antenna_drive_warning_limit_el = lambda x: ValueRange(  # noqa: E731
        *map(Quantity, x)
    )
    antenna_drive_critical_limit_az = lambda x: ValueRange(  # noqa: E731
        *map(Quantity, x)
    )
    antenna_drive_critical_limit_el = lambda x: ValueRange(  # noqa: E731
        *map(Quantity, x)
    )
    antenna_pointing_accuracy = Quantity
    antenna_pointing_parameter_path = Path
    antenna_scan_margin = Quantity
    antenna_max_acceleration_az = Quantity
    antenna_max_acceleration_el = Quantity
    antenna_max_speed_az = Quantity
    antenna_max_speed_el = Quantity
    antenna_speed_to_pulse_factor_az = Quantity
    antenna_speed_to_pulse_factor_el = Quantity
    antenna_command_frequency = int
    antenna_command_offset_sec = float
    ros_service_timeout_sec = float
    ros_communication_deadline_sec = float
    ros_logging_interval_sec = float
    ros_topic_scan_interval_sec = float


class Configuration:

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        self.__config = None
        self.reload()

    def __getitem__(self, key: str) -> Any:
        ret = self.__config.__getitem__(key)
        return self._dotnecst + f"/{ret}" if isinstance(ret, Path) else ret

    def __getattr__(self, key: str) -> Any:
        ret = getattr(self.__config, key)
        return self._dotnecst + f"/{ret}" if isinstance(ret, Path) else ret

    @property
    def _dotnecst(self) -> Path:
        return self.__config_path.rsplit("/", 1)[0]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(file='{self.__config_path}')"

    def __str__(self) -> str:
        return str(self.__config)

    def reload(self) -> None:
        params = self.__find_config()
        new_config = _Cfg(self, params)
        # Attribute validation
        attr_cross_section = set(dir(self.__class__)) & set(new_config.keys())
        dupl_attrs = list(filter(lambda x: not x.startswith("_"), attr_cross_section))
        if dupl_attrs:
            raise NECSTConfigurationError(
                f"Parameters {dupl_attrs} cannot be set; reserved name."
            )
        # Assign after validation
        self.__config = new_config

    def __find_config(self) -> TOMLDocument:
        root_candidates = [DefaultNECSTRoot]
        if EnvVarName.necst_root in os.environ:
            root_candidates.insert(0, os.environ[EnvVarName.necst_root])
        config_file_name = "config.toml"
        candidates = map(lambda x: str(x) + f"/{config_file_name}", root_candidates)

        for path in candidates:
            try:
                contents = read_file(path, localonly=False)
                logger.info(f"Imported configuration file '{path}'")
                self.__config_path = path
                return tomlkit.parse(contents)
            except FileNotFoundError:
                logger.debug(f"Config file not found at {path!r}")

        logger.error(
            "Config file not found, using the default parameters. "
            "To create the file with default parameters, run `neclib.configure()`."
        )
        self.__config_path = str(Path(__file__).parent / "src" / "config.toml")
        return tomlkit.parse(read_file(self.__config_path, localonly=True))

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
    __slots__ = ("_raw_config", "_config_manager", "_prefix", "_config")

    def __init__(
        self,
        config_manager: Configuration,
        config: TOMLDocument,
        prefix: str = "",
        parsed: Dict[str, Any] = None,
    ) -> None:
        self._raw_config = config
        self._config_manager = config_manager
        self._prefix = prefix
        if parsed is None:
            parsed = dict(self.__flatten(config))
        self._config = {}
        for key, value in parsed.items():
            if not self.__norm(key).startswith(self.__norm(self._prefix)):
                continue
            self._config[key] = value

        config_keys = [self.__norm(key) for key in self._config.keys()]
        duplicated_key = [key for key in set(config_keys) if config_keys.count(key) > 1]
        if len(duplicated_key) > 0:
            raise NECSTConfigurationError(
                "Duplicated keys are not allowed in the configuration file: "
                f"{duplicated_key}"
            )

    def __flatten(
        self, data: Dict[str, Any], prefix: str = "", raw: bool = False
    ) -> Generator[Tuple[str, Any], None, None]:
        for key, value in data.items():
            if isinstance(value, Table):
                yield from self.__flatten(value, prefix + key + ".", raw=raw)
            else:
                if raw:
                    yield prefix + key, value
                    continue
                value = value.unwrap() if hasattr(value, "unwrap") else value
                parser = getattr(
                    _Parsers, (prefix + key).replace(".", "_"), lambda x: x
                )
                if (
                    not (prefix + key)
                    .replace(".", "_")
                    .startswith(self._prefix.replace(".", "_"))
                ):
                    continue
                parsed = parser(value)
                parsed = (
                    self._config_manager._dotnecst + f"/{parsed}"
                    if isinstance(parsed, Path)
                    else parsed
                )
                yield prefix + key, parsed

    @property
    def _raw_flat(self) -> Generator[Tuple[str, Any], None, None]:
        yield from self.__flatten(self._raw_config, raw=True)

    def __str__(self) -> str:
        width = max(len(p) for p in self._config.keys()) - len(self._prefix) + 2

        def _prettify(key: str) -> str:
            key, value = key[len(self._prefix) :], self._config.get(key)
            return f"    {key:{width}s}{value!s}    ({type(value).__name__})"

        _parameters = "\n".join(map(_prettify, self._config.keys()))
        return f"NECST configuration (prefix='{self._prefix}')\n{_parameters}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(prefix={self._prefix!r})"

    def __norm(self, key: str) -> str:
        return key.replace(".", "_").lower()

    def __getitem__(self, key: str) -> Any:
        full_key = self._prefix + key
        if full_key in self._config:
            return self._config[full_key]
        if self.__norm(full_key) in map(lambda x: self.__norm(x), self._config):
            for k, v in self._config.items():
                if self.__norm(k) == self.__norm(full_key):
                    return v

        same_prefix = [k for k in self._config if k.startswith(full_key + ".")]
        full_key += "." if len(same_prefix) > 0 else "_"
        return _Cfg(self._config_manager, self._raw_config, full_key)

    def __getattr__(self, key: str) -> Any:
        return self[key]

    def keys(self, full: bool = False) -> KeysView:
        if full:
            return self._config.keys()
        return {k[len(self._prefix) :]: None for k in self._config.keys()}.keys()

    def values(self, full: bool = False) -> ValuesView:
        return self._config.values()

    def items(self, full: bool = False) -> ItemsView:
        if full:
            return self._config.items()
        return {k[len(self._prefix) :]: v for k, v in self._config.items()}.items()

    def __gt__(self, other: Any) -> bool:
        if other is None:
            return True
        if not isinstance(other, (_Cfg, Configuration)):
            return NotImplemented
        if set(self.keys(full=False)) <= set(other.keys(full=False)):
            return False
        lazy_eq = (getattr(self, k) == getattr(other, k) for k in other.keys())
        full_eq = (getattr(self, k) == getattr(other, k) for k in other.keys(full=True))
        return True if all(lazy_eq) or all(full_eq) else False

    def __lt__(self, other: Any) -> bool:
        if other is None:
            return False
        if not isinstance(other, (_Cfg, Configuration)):
            return NotImplemented
        if set(self.keys(full=False)) >= set(other.keys(full=False)):
            return False
        lazy_eq = (getattr(self, k) == getattr(other, k) for k in self.keys())
        full_eq = (getattr(self, k) == getattr(other, k) for k in self.keys(full=True))
        return True if all(lazy_eq) or all(full_eq) else False

    def __eq__(self, other: Any) -> bool:
        if other is None:
            return False
        if not isinstance(other, (_Cfg, Configuration)):
            return NotImplemented
        if set(self.keys(full=False)) != set(other.keys(full=False)):
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

    def __add__(self, other: Any) -> "_Cfg":
        if other is None:
            return self
        if not isinstance(other, (_Cfg, Configuration)):
            return NotImplemented

        if self._prefix == other._prefix:
            new = TOMLDocument()
            for k, v in self._raw_flat:
                if self.__norm(k).startswith(self.__norm(self._prefix)):
                    new[k] = v
            for k, v in other._raw_flat:
                if self.__norm(k).startswith(self.__norm(other._prefix)):
                    if (k in new.keys()) and (new[k] != v):
                        raise ValueError(
                            "Cannot merge configurations with conflicting values"
                        )
                    new[k] = v
            return _Cfg(self._config_manager, new, self._prefix, self._config)
        else:
            new = TOMLDocument()
            self_prefix_len = len(self._prefix)
            other_prefix_len = len(other._prefix)
            for k, v in self._raw_flat:
                if self.__norm(k).startswith(self.__norm(self._prefix)):
                    new[k[self_prefix_len:]] = v
            for k, v in other._raw_flat:
                if self.__norm(k).startswith(self.__norm(other._prefix)):
                    if (k in new.keys()) and (new[k] != v):
                        raise ValueError(
                            "Cannot merge configurations with conflicting values"
                        )
                    new[k[other_prefix_len:]] = v
            return _Cfg(self._config_manager, new, "")

    __radd__ = __add__


config = Configuration()
configure = Configuration.configure
