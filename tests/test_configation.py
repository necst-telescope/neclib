import os
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from astropy.coordinates import EarthLocation

from neclib import configure


@pytest.fixture
def mock_home_dir(tmp_path_factory):
    home = tmp_path_factory.mktemp("username")
    with patch("pathlib.Path.home", return_value=home), patch(
        "neclib.configuration.DefaultNECSTRoot", home / ".necst"
    ), patch("neclib.configuration.DefaultConfigPath", home / ".necst" / "config.toml"):
        yield


@pytest.fixture
def dot_necst_dir(mock_home_dir) -> Path:
    path = Path.home() / ".necst"
    path.mkdir()
    return path


@pytest.fixture
def custom_necst_root_dir(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("home")


@pytest.mark.usefixtures("mock_home_dir")
class TestConfigure:

    expected_default_config = {
        "observatory": "OMU1P85M",
        "location": EarthLocation(
            lon="138.472153deg", lat="35.940874deg", height="1386.0m"
        ),
    }
    expected_custom_config = {
        "observatory": "NANTEN2",
        "location": EarthLocation(
            lon="-67.70308139deg", lat="-22.96995611deg", height="4863.85m"
        ),
        "not_supported_entry": 1,
    }

    def test_configure_no_config(self, dot_necst_dir: Path):
        assert not (dot_necst_dir / "config.toml").exists()

        config = configure()
        assert config.__dict__ == self.expected_default_config
        assert (dot_necst_dir / "config.toml").exists()

    def test_configure_no_env(self, data_dir: Path, dot_necst_dir: Path):
        shutil.copyfile(
            data_dir / "sample_config_customized.toml", dot_necst_dir / "config.toml"
        )
        assert (dot_necst_dir / "config.toml").exists()

        config = configure()
        assert config.__dict__ == self.expected_custom_config

    def test_configure_with_env_but_no_config(
        self, data_dir: Path, dot_necst_dir: Path, custom_necst_root_dir: Path
    ):
        os.environ["NECST_ROOT"] = str(custom_necst_root_dir)
        shutil.copyfile(
            data_dir / "sample_config_customized.toml", dot_necst_dir / "config.toml"
        )
        assert (dot_necst_dir / "config.toml").exists()
        assert not (custom_necst_root_dir / "config.toml").exists()

        config = configure()
        assert config.__dict__ == self.expected_custom_config

    def test_configure_with_env(
        self, data_dir: Path, dot_necst_dir: Path, custom_necst_root_dir: Path
    ):
        os.environ["NECST_ROOT"] = str(custom_necst_root_dir)
        shutil.copyfile(
            data_dir / "sample_config_customized.toml",
            custom_necst_root_dir / "config.toml",
        )
        shutil.copyfile(data_dir / "sample_config.toml", dot_necst_dir / "config.toml")
        assert (custom_necst_root_dir / "config.toml").exists()
        assert (dot_necst_dir / "config.toml").exists()

        config = configure()
        assert config.__dict__ == self.expected_custom_config
