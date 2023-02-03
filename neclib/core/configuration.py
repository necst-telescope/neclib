import os
import shutil
from collections.abc import ItemsView, KeysView, ValuesView
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

from astropy.coordinates import EarthLocation
from astropy.units import Quantity

from . import environ
from .data_type import RichParameters, ValueRange
from .exceptions import NECSTParameterNameError
from .files import read
from .inform import get_logger

DefaultNECSTRoot = Path.home() / ".necst"
logger = get_logger(__name__)


class Configuration(RichParameters):
    _instance = None

    def __new__(cls, __prefix: str = "", /, **kwargs):
        if cls._instance is None:
            cls._instance = super(Configuration, cls).__new__(cls)
        return cls._instance

    @property
    def _dotnecst(self) -> str:
        from urllib.parse import urlparse

        try:
            url = urlparse(self._path)
            scheme = f"{url.scheme}://" if url.scheme else ""
            path = url.path
            path = path.decode("utf-8") if isinstance(path, bytes) else path
            return scheme + str(Path(path).parent)
        except Exception:
            return ""

    def reload(self):
        path = find_config()
        self = self.__class__.from_file(path)

    @classmethod
    def configure(cls):
        """Create config file under ``$HOME/.necst``"""
        DefaultNECSTRoot.mkdir(exist_ok=True)
        for file in (Path(__file__).parent / "src").glob("*.toml"):
            _target_path = DefaultNECSTRoot / file.name
            if _target_path.exists():
                logger.error(f"'{_target_path}' already exists, skipping...")
                continue
            shutil.copyfile(file, _target_path)
        cls().reload()

    @property
    def _unwrapped(self) -> Dict[str, Any]:
        return {k: v.value for k, v in self._parameters.items()}

    def keys(self) -> KeysView:
        return self._unwrapped.keys()

    def values(self) -> ValuesView:
        return self._unwrapped.values()

    def items(self) -> ItemsView:
        return self._unwrapped.items()

    def __getitem__(self, key: str, /):
        item = super().__getitem__(key)
        if isinstance(item, Path):
            item = os.path.join(self._dotnecst, item)
        return item

    def __getattr__(self, key: str, /):
        attr = super().__getattr__(key)
        if isinstance(attr, Path):
            attr = os.path.join(self._dotnecst, attr)
        return attr

    def __add__(self, other: Any, /):
        if other is None:
            return self
        if not isinstance(other, self.__class__):
            return NotImplemented

        if self._prefix == other._prefix:
            parameters = deepcopy(self._parameters)
            for k, v in other._parameters.items():
                if (k in parameters) and (parameters[k] != v):
                    raise KeyError(
                        f"Conflicting values for {k!r} found: {parameters[k]} and {v}."
                    )
                parameters[k] = v
            parameters.update(other._parameters)
            inst = self.__class__(self._prefix, **parameters)
            return inst

        length = len(self._prefix)
        prefix_stripped = {
            k[length:]: v
            for k, v in self._parameters.items()
            if k.startswith(self._prefix)
        }
        length = len(other._prefix)
        prefix_stripped_other = {
            k[length:]: v
            for k, v in other._parameters.items()
            if k.startswith(other._prefix)
        }
        for k, v in prefix_stripped_other.items():
            if (k in prefix_stripped) and (prefix_stripped[k] != v):
                raise KeyError(
                    f"Conflicting values for {k!r} found: {prefix_stripped[k]} and {v}."
                )
            prefix_stripped[k] = v
        return self.__class__(self._prefix, **prefix_stripped)

    __radd__ = __add__


def find_config() -> str:
    root_candidates = [str(DefaultNECSTRoot)]
    specified = environ.necst_root.get()
    if specified is not None:
        root_candidates.insert(0, specified)
    config_file_name = "config.toml"
    candidates = map(lambda x: os.path.join(x, config_file_name), root_candidates)

    for path in candidates:
        try:
            read(path)
            return path
        except FileNotFoundError:
            logger.debug(f"Config file not found at {path!r}")

    logger.error(
        "Config file not found, using the default parameters. "
        "To create the file with default parameters, run `neclib.configure()`."
    )
    config_path = str(Path(__file__).parent / "src" / "config.toml")
    return str(config_path)


parsers = dict(
    location=lambda x: EarthLocation(**x),
    antenna_drive_range_az=lambda x: ValueRange(*map(Quantity, x)),
    antenna_drive_range_el=lambda x: ValueRange(*map(Quantity, x)),
    antenna_drive_warning_limit_az=lambda x: ValueRange(*map(Quantity, x)),
    antenna_drive_warning_limit_el=lambda x: ValueRange(*map(Quantity, x)),
    antenna_drive_critical_limit_az=lambda x: ValueRange(*map(Quantity, x)),
    antenna_drive_critical_limit_el=lambda x: ValueRange(*map(Quantity, x)),
    antenna_pointing_parameter_path=Path,
)

config = Configuration.from_file(find_config())

for key, parser in parsers.items():
    try:
        config.attach_parsers(**{key: parser})
    except NECSTParameterNameError:
        pass

configure = Configuration.configure
