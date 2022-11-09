__all__ = ["configure", "config"]

import difflib
import os
import shutil
from collections import UserDict
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict

import astropy.units as u
from astropy.coordinates import EarthLocation
from tomlkit.toml_file import TOMLFile

from . import EnvVarName, get_logger
from .exceptions import ConfigurationError
from .utils import ValueRange

logger = get_logger(__name__)


class _ConfigParsers(UserDict):
    def __missing__(self, key: str) -> Callable[[Any], Any]:
        if key in self.keys():
            return self[key]
        similar_keys = difflib.get_close_matches(key.lower(), self.keys(), cutoff=0.85)
        if similar_keys:
            logger.info(
                f"Parser for {key!r} not found, instead using raw value. "
                f"Similarly named parameters : {similar_keys}"
            )
        return lambda x: x


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

    DefaultNECSTRoot = Path.home() / ".necst"
    DefaultConfigPath = DefaultNECSTRoot / "config.toml"

    def __new__(cls):
        if cls._instance is None:
            return super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.__parameters = {}
        self.reload()

    def __repr__(self) -> str:
        return f"Configuration(file='{self.__config_path}')"

    def __str__(self) -> str:
        length = max(len(p) for p in self.__parameters)

        def _prettify(key: str):
            value = self.__parameters.get(key, None)
            return f"    {key:{length+2}s}{value!s}    ({type(value).__name__})"

        _parameters = "\n".join([_prettify(k) for k in self.__parameters])
        return f"NECST configuration\n{_parameters}"

    def reload(self):
        """Reload the parameters, in case the config file is updated.

        .. WARNING::

            Manually set parameters will be lost on reload.

        """
        self.__config_path = self.__find_config_path()
        self.__dotnecst = self.__config_path.parent
        self.__parameters = self.__parse()

    def __getattr__(self, key: str) -> Any:
        param = self.__parameters.get(key, None)
        if param is not None:
            return param
        param = self.__parameters.get(key.lower(), None)
        if param is not None:
            return param

        prefix = key + "_"
        prefix_length = len(prefix)
        _match = {
            k[prefix_length:]: self.__parameters[k]
            for k in self.__parameters
            if k.lower().startswith(prefix.lower())
        }
        return SimpleNamespace(**_match) if _match else None

    def __get_parser(self) -> _ConfigParsers:
        _parsers: Dict[str, Callable[[Any], Any]] = {
            "observatory": str,
            "location": lambda x: EarthLocation(**x),
            "simulator": bool,
            "record_root": Path,
            "alert_interval_sec": float,
            "antenna_pid_param_az": list,
            "antenna_pid_param_el": list,
            "antenna_drive_range_az": lambda x: ValueRange(*map(u.Quantity, x)),
            "antenna_drive_range_el": lambda x: ValueRange(*map(u.Quantity, x)),
            "antenna_drive_warning_limit_az": lambda x: ValueRange(*map(u.Quantity, x)),
            "antenna_drive_warning_limit_el": lambda x: ValueRange(*map(u.Quantity, x)),
            "antenna_drive_critical_limit_az": lambda x: ValueRange(
                *map(u.Quantity, x)
            ),
            "antenna_drive_critical_limit_el": lambda x: ValueRange(
                *map(u.Quantity, x)
            ),
            "antenna_pointing_accuracy": u.Quantity,
            "antenna_pointing_parameter_path": lambda x: self.__dotnecst / Path(x),
            "antenna_max_acceleration_az": u.Quantity,
            "antenna_max_acceleration_el": u.Quantity,
            "antenna_max_speed_az": u.Quantity,
            "antenna_max_speed_el": u.Quantity,
            "antenna_speed_to_pulse_factor_az": u.Quantity,
            "antenna_speed_to_pulse_factor_el": u.Quantity,
            "antenna_command_frequency": int,
            "antenna_command_offset_sec": float,
            "ros_service_timeout_sec": float,
            "ros_communication_deadline_sec": float,
            "ros_logging_interval_sec": float,
            "ros_topic_scan_interval_sec": float,
        }
        return _ConfigParsers(_parsers)

    def __parse(self) -> Dict[str, Any]:
        raw_config = TOMLFile(self.__config_path).read().unwrap()
        parser = self.__get_parser()

        parsed = {}
        for k, v in raw_config.items():
            k = k.lower()

            errmsg = f"Parameter {k!r} cannot be set; "
            if k in vars(self.__class__).keys():
                raise ConfigurationError(errmsg + "reserved name.")
            if k in parsed:
                raise ConfigurationError(errmsg + "duplicated definition.")

            parsed[k] = parser[k](v)
        return parsed

    def __find_config_path(self) -> Path:
        candidates = [self.DefaultNECSTRoot]
        if EnvVarName.necst_root in os.environ.keys():
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
        cls.DefaultNECSTRoot.mkdir(exist_ok=True)
        for filename in ["config.toml", "pointing_param.toml"]:
            _target_path = cls.DefaultNECSTRoot / filename
            if _target_path.exists():
                logger.error(f"'{_target_path}' already exists, skipping...")
                continue
            shutil.copyfile(Path(__file__).parent / "src" / filename, _target_path)
        cls().reload()


configure = Configuration.configure
config = Configuration()
