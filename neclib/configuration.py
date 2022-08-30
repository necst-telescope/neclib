import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import astropy.units as u
from astropy.coordinates import EarthLocation
from tomlkit.toml_file import TOMLFile

from neclib import logger
from .typing import PathLike


@dataclass
class EnvVarName:
    root: str = "NECST_ROOT"
    ros2_ws: str = "ROS2_WS"
    domain_id: str = "ROS_DOMAIN_ID"
    record_root: str = "NECST_RECORD_ROOT"


DefaultNECSTRoot = Path.home() / ".necst"
DefaultConfigPath = DefaultNECSTRoot / "config.toml"


def configure() -> SimpleNamespace:
    candidates = [DefaultNECSTRoot]
    if EnvVarName.root in os.environ.keys():
        candidates.insert(0, Path(os.environ[EnvVarName.root]))

    for path in candidates:
        config_path = path / "config.toml"
        if config_path.exists():
            logger.info(f"Using configuration file '{config_path}'")
            return parse_config(config_path)

    logger.info(
        "Configuration file not found. Creating the file with default settings"
        f"at '{DefaultConfigPath}'"
    )
    create_defaults()
    return parse_config(DefaultConfigPath)


def create_defaults() -> None:
    DefaultConfigPath.parent.mkdir(exist_ok=True)
    if DefaultConfigPath.exists():
        raise FileExistsError(f"{DefaultConfigPath} already exists.")
    shutil.copyfile(
        Path(__file__).parent / "src" / "config.toml",
        DefaultConfigPath,
    )


CONFIG_PARSERS = {
    "observatory": str,
    "location": lambda x: EarthLocation(**x),
    "antenna_pid_param": lambda x: SimpleNamespace(**x),
    "antenna_drive_range": lambda x: SimpleNamespace(
        **{k: u.Quantity(list(map(u.Quantity, v))) for k, v in x.items()}
    ),
    "antenna_drive_softlimit": lambda x: SimpleNamespace(
        **{k: u.Quantity(list(map(u.Quantity, v))) for k, v in x.items()}
    ),
    "antenna_pointing_accuracy": u.Quantity,
    "ros_service_timeout_sec": float,
}


def parse_config(path: PathLike) -> SimpleNamespace:
    raw_config = TOMLFile(path).read()

    def _parse(k: str, v: Any) -> Any:
        try:
            return CONFIG_PARSERS[k.lower()](v)
        except KeyError:
            logger.warning(
                f"Parser for '{k}' not found. Using raw value : {v} ({type(v)})."
            )
            return v

    config = {k.lower(): _parse(k, v) for k, v in raw_config.items()}
    return SimpleNamespace(**config)
