import os
import re
import shutil
from collections.abc import ItemsView, KeysView, ValuesView
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Generator, Union

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
        return self._dotnecst / ret if isinstance(ret, Path) else ret

    def __getattr__(self, key: str) -> Any:
        ret = getattr(self.__config, key)
        return self._dotnecst / ret if isinstance(ret, Path) else ret

    @property
    def _dotnecst(self) -> Path:
        return self.__config_path.parent

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(file='{self.__config_path}')"

    def __str__(self) -> str:
        return str(self.__config)

    def reload(self) -> None:
        self.__config_path = self.__find_config()
        params = tomlkit.parse(read_file(self.__config_path, localonly=True))
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

    def __find_config(self) -> Path:
        root_candidates = [DefaultNECSTRoot]
        if EnvVarName.necst_root in os.environ:
            root_candidates.insert(0, os.environ[EnvVarName.necst_root])
        config_file_name = os.environ.get(EnvVarName.necst_config_name, "config.toml")
        candidates = map(lambda x: str(x) + f"/{config_file_name}", root_candidates)

        for path in candidates:
            try:
                read_file(path, localonly=True)
                found = Path(re.sub(r".*://", "", path))
                logger.info(f"Imported configuration file '{found}'")
                return found
            except FileNotFoundError:
                pass

            try:
                saveto = DefaultNECSTRoot / "config.toml"
                read_file(path, localonly=False, saveto=saveto, overwrite=True)
                logger.info(
                    f"Imported configuration file '{path}', "
                    f"which was saved to '{saveto}'"
                )
                return saveto
            except FileNotFoundError:
                pass

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


class TOMLDict:
    def __init__(self, data: TOMLDocument) -> None:
        self._toml_data = data
        self._native_data = self._toml_data.unwrap()
        for k, v in self.flat:
            *namespace, _k = k.split(".")
            ref = self._native_data
            for ns in namespace:
                ref = ref[ns]
            v = v.unwrap() if hasattr(v, "unwrap") else v
            ref[_k] = self.get_parser(k)(v)

    def get_parser(self, key: str) -> Callable[[Any], Any]:
        return getattr(_Parsers, key.replace(".", "_"), lambda x: x)

    def get(self, key: str, full: bool = False, parse: bool = False) -> Any:
        key = key.lower()

        *namespace, key = key.split(".")
        extracted = deepcopy(self._native_data) if parse else deepcopy(self._toml_data)
        ref = extracted
        for ns in namespace:
            for k in ref.copy():
                if ns != k.lower():
                    ref.pop(k)
            ref = ref[ns]

        if key in ref:
            for k in ref.copy():
                if key != k.lower():
                    ref.pop(k)
            return extracted if full else ref[key]
        else:
            for k in ref.copy():
                if not k.lower().startswith(key):
                    ref.pop(k)
            return extracted if full else ref

    def set(self, key: str, value: Any) -> None:
        *namespace, key = key.split(".")
        ref_toml = self._toml_data
        ref_native = self._native_data
        for ns in namespace:
            if ns not in ref_toml:
                ref_toml[ns] = Table()
                ref_native[ns] = {}
            ref_toml = ref_toml[ns]
            ref_native = ref_native[ns]
        ref_toml[key] = value
        ref_native[key] = self.get_parser(key)(value)

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)

    @property
    def flat(self) -> Generator[Any, None, None]:
        def generate_flat(data: Any, prefix: str = "") -> Generator[Any, None, None]:
            for key, value in data.items():
                if isinstance(value, Table):
                    yield from generate_flat(value, prefix + key + ".")
                else:
                    yield prefix + key, self._native_data.get(prefix + key, value)

        yield from generate_flat(self._toml_data)

    @property
    def raw_flat(self) -> Generator[Any, None, None]:
        def generate_flat(data: Any, prefix: str = "") -> Generator[Any, None, None]:
            for key, value in data.items():
                if isinstance(value, Table):
                    yield from generate_flat(value, prefix + key + ".")
                else:
                    yield prefix + key, value

        yield from generate_flat(self._toml_data)

    def flat_keys(self) -> Generator[str, None, None]:
        for key, _ in self.flat:
            yield key

    raw_flat_keys = flat_keys

    def flat_values(self) -> Generator[Any, None, None]:
        for _, value in self.flat:
            yield value

    def raw_flat_values(self) -> Generator[Any, None, None]:
        for _, value in self.raw_flat:
            yield value

    flat_items = flat

    def __getitem__(self, key: str) -> Any:
        return self.get(key)

    def __str__(self) -> str:
        return str(self._toml_data)

    def __repr__(self) -> str:
        return repr(self._toml_data)

    @property
    def raw(self) -> TOMLDocument:
        return self._toml_data


class _Cfg:
    __slots__ = ["_config", "_prefix", "_config_manager"]

    def __init__(
        self,
        config_manager: Configuration,
        config: Union[Table, TOMLDocument],
        prefix: str = "",
    ) -> None:
        self._prefix = prefix
        self._config = TOMLDict(config)
        self._config_manager = config_manager

        config_keys = [key.lower() for key in self._config.flat_keys()]
        duplicated_key = [key for key in set(config_keys) if config_keys.count(key) > 1]
        if len(duplicated_key) > 0:
            raise NECSTConfigurationError(
                "Duplicated keys are not allowed in the configuration file: "
                f"{duplicated_key}"
            )

    def __getattr__(self, key: str) -> Any:
        return self.__getitem__(key)

    @property
    def _dotnecst(self) -> Path:
        return self._config_manager._dotnecst

    def __getitem__(self, key: str) -> Any:
        full_key = (self._prefix + key).lower()
        config_keys = [k.lower() for k in self._config.flat_keys()]
        if full_key in config_keys:
            ret = self._config.get(full_key, False, True)
            return self._dotnecst / ret if isinstance(ret, Path) else ret
        key_is_namespace = bool(
            [k for k in config_keys if k.startswith(full_key + ".")]
        )
        if key_is_namespace:
            return _Cfg(
                self._config_manager, self._config.get(full_key, True), full_key + "."
            )
        existent_key = [k for k in config_keys if k.startswith(full_key)]
        if existent_key:
            return _Cfg(
                self._config_manager, self._config.get(full_key, True), full_key + "_"
            )
        return None

    def __str__(self) -> str:
        width = max(len(p) for p in self._config.flat_keys()) - len(self._prefix) + 2

        def _prretify(key: str) -> str:
            key, value = key[len(self._prefix) :], self._config.get(key, False, True)
            return f"    {key:{width}s}{value!s}    ({type(value).__name__})"

        _parameters = "\n".join(map(_prretify, self._config.flat_keys()))
        return f"NECST configuration (prefix='{self._prefix}')\n{_parameters}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(prefix='{self._prefix}')"

    def keys(self, full: bool = False) -> KeysView:
        flattened = self._config.flat
        if not full:
            prefix_len = len(self._prefix)
            flattened = map(lambda x: (x[0][prefix_len:], x[1]), flattened)
        return dict(flattened).keys()

    def values(self, raw: bool = False) -> ValuesView:
        flattened = self._config.raw_flat if raw else self._config.flat
        flattened = map(
            lambda x: (x[0], self._dotnecst / x[1] if isinstance(x[1], Path) else x[1]),
            flattened,
        )
        if raw:
            return dict(flattened).values()
        return dict((k, self[k]) for k, _ in flattened).values()

    def items(self, full: bool = False, raw: bool = False) -> ItemsView:
        flattened = self._config.raw_flat if raw else self._config.flat
        flattened = map(
            lambda x: (x[0], self._dotnecst / x[1] if isinstance(x[1], Path) else x[1]),
            flattened,
        )
        if not full:
            prefix_len = len(self._prefix)
            flattened = map(lambda x: (x[0][prefix_len:], x[1]), flattened)
        if raw:
            return dict(flattened).items()
        return dict((k, self[k]) for k, _ in flattened).items()

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
            new_config = TOMLDict(deepcopy(self._config))
            for k, v in other.items(full=True, raw=True):
                new_config[k] = v
            for k, v in self.items(full=True, raw=True):
                if (k in new_config.flat_keys()) and (new_config.get(k, False) != v):
                    raise ValueError(
                        "Cannot merge configurations with different values"
                    )
                new_config[k] = v
            return _Cfg(self._config_manager, new_config.raw, self._prefix)
        else:
            new_config = TOMLDict(TOMLDocument())
            for k, v in self.items(full=False, raw=True):
                new_config[k] = v
            for k, v in other.items(full=False, raw=True):
                if (k in new_config.flat_keys()) and (new_config.get(k, False) != v):
                    raise ValueError(
                        "Cannot merge configurations with different values"
                    )
                new_config[k] = v
            return _Cfg(self._config_manager, new_config.raw, "")

    __radd__ = __add__


config = Configuration()
configure = Configuration.configure
