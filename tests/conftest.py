import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Type

import pytest
from astropy.coordinates import EarthLocation

from neclib import config

from .types import ConfiguredTester

data_dir = Path(__file__).parent / "_data"


@pytest.fixture(name="data_dir")
def data_dir_fixture() -> Path:
    return Path(__file__).parent / "_data"


def configured_tester_factory(config_dir: str) -> Type[ConfiguredTester]:
    class Tester:
        @classmethod
        def setup_class(cls) -> None:
            cls.original = os.environ.get("NECST_ROOT", None)
            os.environ["NECST_ROOT"] = str(data_dir / config_dir)
            config.reload()

        @classmethod
        def teardown_class(cls) -> None:
            if cls.original is None:
                del os.environ["NECST_ROOT"]
            else:
                os.environ["NECST_ROOT"] = cls.original
            config.reload()

    return Tester


@contextmanager
def tmp_environ(**kwargs) -> Generator[None, None, None]:
    original = {k: os.environ.get(k, None) for k in kwargs.keys()}
    for k, v in kwargs.items():
        os.environ[k] = v
    try:
        yield
    finally:
        for k, v in original.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


@pytest.fixture
def location() -> EarthLocation:
    return config.location  # type: ignore
