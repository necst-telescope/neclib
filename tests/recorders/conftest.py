from pathlib import Path

import pytest


@pytest.fixture
def data_root(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("data")
