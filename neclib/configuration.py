__all__ = ["configure", "config"]

import difflib
import os
import shutil
from collections import UserDict
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, List

import astropy.units as u
from astropy.coordinates import EarthLocation
from tomlkit.toml_file import TOMLFile

from neclib import logger


@dataclass
class EnvVarName:
    necst_root: str = "NECST_ROOT"
    ros2_ws: str = "ROS2_WS"
    domain_id: str = "ROS_DOMAIN_ID"
    record_root: str = "NECST_RECORD_ROOT"


class _ConfigParsers(UserDict):
    def __missing__(self, key: str) -> Any:
        if key in self.keys():
            return self[key]
        similar_keys = difflib.get_close_matches(key.lower(), self.keys())
        if similar_keys:
            logger.info(
                f"Parser for '{key}' not found, instead using raw value. "
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
        self.__parameters = []
        self.reload()

    def __repr__(self):
        _parameters = ", ".join([f"{k}={self.__dict__[k]}" for k in self.__parameters])
        return f"Configuration({_parameters})"

    def reload(self):
        """Reload the parameters, in case the config file is updated."""
        for param in self.__parameters:
            del self.__dict__[param]
        self.__config_path = self.__find_config_path()
        self.__dotnecst = self.__config_path.parent
        self.__parameters = self.__parse()

    def __getattr__(self, key: str) -> Any:
        prefix = key + "_"
        prefix_length = len(prefix)
        match = {
            k[prefix_length:]: getattr(self, k)
            for k in self.__parameters
            if k.startswith(prefix)
        }
        return SimpleNamespace(**match)

    def __get_parser(self) -> _ConfigParsers:
        _parsers: Dict[str, Callable[[Any], Any]] = {
            "observatory": str,
            "location": lambda x: EarthLocation(**x),
            "antenna_pid_param_az": list,
            "antenna_pid_param_el": list,
            "antenna_drive_range_az": lambda x: list(map(u.Quantity, x)),
            "antenna_drive_range_el": lambda x: list(map(u.Quantity, x)),
            "antenna_drive_softlimit_az": lambda x: list(map(u.Quantity, x)),
            "antenna_drive_softlimit_el": lambda x: list(map(u.Quantity, x)),
            "antenna_pointing_accuracy": u.Quantity,
            "pointing_parameter_path": lambda x: self.__dotnecst / Path(x),
            "ros_service_timeout_sec": float,
        }
        return _ConfigParsers(_parsers)

    def __parse(self) -> List[str]:
        raw_config = TOMLFile(self.__config_path).read()
        parser = self.__get_parser()
        for k, v in raw_config.items():
            setattr(self, k, parser[k](v))
        return list(raw_config.keys())

    def __find_config_path(self) -> Path:
        candidates = [self.DefaultNECSTRoot]
        if EnvVarName.necst_root in os.environ.keys():
            candidates.insert(0, Path(os.environ[EnvVarName.necst_root]))

        for path in candidates:
            config_path = path / "config.toml"
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
                logger.error(f"'{cls.DefaultConfigPath}' already exists, skipping...")
                continue
            shutil.copyfile(Path(__file__).parent / "src" / filename, _target_path)
        cls().reload()


configure = Configuration.configure
config = Configuration()
