import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import pytest
from astropy.coordinates import EarthLocation

from neclib import config


@pytest.fixture
def data_dir() -> Path:
    return Path(__file__).parent / "_data"


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
    return config.location
