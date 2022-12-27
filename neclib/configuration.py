__all__ = ["config", "configure"]

import os
import re
import shutil
from collections.abc import ItemsView, KeysView, ValuesView
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import tomlkit
from astropy.coordinates import EarthLocation
from astropy.units import Quantity
from tomlkit import TOMLDocument
from tomlkit.items import Table

from . import EnvVarName, get_logger
from .exceptions import NECSTConfigurationError
from .utils import ValueRange, read_file

logger = get_logger(__name__)

DefaultNECSTRoot = Path.home() / ".necst"


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

    @property
    def _dotnecst(self) -> Path:
        return self.__config_path.parent

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(file='{self.__config_path}')"

    def __str__(self) -> str:
        return str(self.__config)

    def __getattr__(self, key: str) -> Optional[Any]:
        return getattr(self.__config, key, None)

    def __getitem__(self, key: str) -> Optional[Any]:
        return self.__config[key]

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


class _Cfg:

    __slots__ = ["_config", "_prefix", "_raw_config", "_config_manager"]

    def __init__(
        self,
        config_manager: Configuration,
        config: Union[Table, TOMLDocument],
        prefix: str = "",
    ) -> None:
        self._prefix = prefix
        self._config_manager = config_manager
        self._config = dict(self._parse(config))
        self._raw_config = config

        if len(set(map(lambda x: x.lower(), self._raw_config))) != len(
            self._raw_config
        ):
            raise NECSTConfigurationError(
                "Duplicated keys are not allowed in the configuration file."
            )

    def _parse(
        self, config: Union[Table, TOMLDocument], prefix: Optional[str] = ""
    ) -> dict:
        for key, value in config.items():
            key, prefix = key.lower(), prefix.lower()
            if isinstance(value, Table):
                yield from self._parse(value, prefix=prefix + key + "::")
            elif (key != "_") and key.startswith("_") or (prefix + key).startswith("_"):
                raise NECSTConfigurationError(
                    f"Parameter {key!r} cannot be assigned; "
                    "name starts with `_` is invalid"
                )
            else:
                value = value.unwrap() if hasattr(value, "unwrap") else value
                parser = getattr(_Parsers, prefix.replace("::", "_") + key, None)
                parsed = value if parser is None else parser(value)
                parsed = (
                    self._config_manager._dotnecst / parsed
                    if isinstance(parsed, Path)
                    else parsed
                )
                prefix = "" if prefix == "" else prefix.rsplit("::", 1)[0] + "::"
                yield prefix + key, parsed

    def __extract_dict(
        self, key: str, dict_: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], str]:
        *namespace, prefix = key.strip("::").split("::")
        ret = new_dict = dict_.__class__()
        for ns in namespace:
            dict_ = dict_[ns]
            new_dict[ns] = {}
            new_dict = new_dict[ns]

        if prefix in dict_:
            new_dict[prefix] = dict_[prefix]
            return ret, "::".join([*namespace, prefix]) + "::"
        else:
            for k, v in dict_.items():
                if k.startswith(prefix):
                    new_dict[k] = v
            return ret, "::".join([*namespace, prefix]) + "_"

    def __getitem__(self, key: str) -> Any:
        key = key.lower()
        if key in self._config:
            return self._config[key]

        absolute_prefix = self._prefix + key.strip("_")
        if absolute_prefix in self._config:
            return self._config[absolute_prefix]

        extracted, prefix = self.__extract_dict(absolute_prefix, self._raw_config)
        if len(extracted) == 0:
            return
        return _Cfg(self._config_manager, extracted, prefix=prefix)

    def __getattr__(self, key: str) -> Any:
        return self[key]

    def __str__(self) -> str:
        width = max(len(p) for p in self._config.keys()) - len(self._prefix) + 2

        def _prretify(key: str) -> str:
            key, value = key[len(self._prefix) :], self._config.get(key)
            return f"    {key:{width}s}{value!s}    ({type(value).__name__})"

        _parameters = "\n".join(map(_prretify, self._config.keys()))
        return f"NECST configuration (prefix='{self._prefix}')\n{_parameters}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(prefix='{self._prefix}')"

    def keys(self, full: bool = False) -> KeysView:
        prefix_length = len(self._prefix)
        if full:
            p = self._config
        else:
            p = map(lambda x: (x[0][prefix_length:], x[1]), self._config.items())
        return dict(p).keys()

    def values(self) -> ValuesView:
        prefix_length = len(self._prefix)
        p = map(lambda x: (x[0][prefix_length:], x[1]), self._config.items())
        return dict(p).values()

    def items(self, full: bool = False) -> ItemsView:
        prefix_length = len(self._prefix)
        if full:
            p = self._config
        else:
            p = map(lambda x: (x[0][prefix_length:], x[1]), self._config.items())
        return dict(p).items()

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
