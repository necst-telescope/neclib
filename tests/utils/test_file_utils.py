from pathlib import Path

import pytest

from neclib.utils import read_file


@pytest.fixture
def home_dir(tmp_path_factory) -> Path:
    home = tmp_path_factory.mktemp("username")
    return home


class TestReadFile:
    def test_read_text(self, data_dir):
        assert read_file(data_dir / "sample_config_customized.toml").startswith(
            'observatory = "NANTEN2"'
        )

    def test_read_text_then_write(self, home_dir, data_dir):
        read_file(
            data_dir / "sample_config_customized.toml", saveto=home_dir / "config.toml"
        )
        assert read_file(home_dir / "config.toml").startswith('observatory = "NANTEN2"')
