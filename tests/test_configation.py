import os
import shutil
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import astropy.units as u
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
        "antenna_pid_param": SimpleNamespace(az=[1.5, 0.0, 0.0], el=[1.5, 0, 0.0]),
        "antenna_drive_range": SimpleNamespace(
            az=[0 << u.deg, 360 << u.deg], el=[10 << u.deg, 90 << u.deg]
        ),
        "antenna_drive_softlimit": SimpleNamespace(
            az=[10 << u.deg, 350 << u.deg], el=[15 << u.deg, 80 << u.deg]
        ),
        "antenna_pointing_accuracy": 10 << u.arcsec,
        "ros_service_timeout_sec": 10,
    }
    expected_custom_config = {
        "observatory": "NANTEN2",
        "location": EarthLocation(
            lon="-67.70308139deg", lat="-22.96995611deg", height="4863.85m"
        ),
        "not_supported_entry": 1,
        "antenna_pid_param": SimpleNamespace(az=[2.2, 0.0, 0.0], el=[2.2, 0, 0.0]),
        "antenna_drive_range": SimpleNamespace(
            az=[-270, 270] << u.deg, el=[0, 90] << u.deg
        ),
        "antenna_drive_softlimit": SimpleNamespace(
            az=[-240, 240] << u.deg, el=[20, 80] << u.deg
        ),
        "antenna_pointing_accuracy": 3 << u.arcsec,
        "ros_service_timeout_sec": 10,
    }

    def test_configure_no_config(self, dot_necst_dir: Path):
        assert not (dot_necst_dir / "config.toml").exists()

        config = configure()
        for actual, expected in zip(config.__dict__, self.expected_default_config):
            try:
                equality = actual == expected
                assert equality if isinstance(equality, bool) else all(equality)
            except ValueError:
                print("Couldn't determine equality of encapsulated sequence")
        assert (dot_necst_dir / "config.toml").exists()

    def test_configure_no_env(self, data_dir: Path, dot_necst_dir: Path):
        shutil.copyfile(
            data_dir / "sample_config_customized.toml", dot_necst_dir / "config.toml"
        )
        assert (dot_necst_dir / "config.toml").exists()

        config = configure()
        for actual, expected in zip(config.__dict__, self.expected_custom_config):
            try:
                equality = actual == expected
                assert equality if isinstance(equality, bool) else all(equality)
            except ValueError:
                print("Couldn't determine equality of encapsulated sequence")

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
        for actual, expected in zip(config.__dict__, self.expected_custom_config):
            try:
                equality = actual == expected
                assert equality if isinstance(equality, bool) else all(equality)
            except ValueError:
                print("Couldn't determine equality of encapsulated sequence")

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
        for actual, expected in zip(config.__dict__, self.expected_custom_config):
            try:
                equality = actual == expected
                assert equality if isinstance(equality, bool) else all(equality)
            except ValueError:
                print("Couldn't determine equality of encapsulated sequence")
