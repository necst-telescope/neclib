import os
import shutil
from pathlib import Path
from typing import get_args
from unittest.mock import patch

import astropy.units as u
import pytest
from astropy.coordinates import EarthLocation

from neclib import ConfigurationError, config, configure
from neclib.utils import ValueRange
from neclib.typing import Boolean


@pytest.fixture
def mock_home_dir(tmp_path_factory):
    home = tmp_path_factory.mktemp("username")
    default_necst_root = "neclib.configuration.DefaultNECSTRoot"
    default_config_path = "neclib.configuration.DefaultConfigPath"
    with patch("pathlib.Path.home", return_value=home), patch(
        default_necst_root, home / ".necst"
    ), patch(default_config_path, home / ".necst" / "config.toml"):
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
        "antenna_pid_param_az": [1.5, 0.0, 0.0],
        "antenna_pid_param_el": [1.5, 0.0, 0.0],
        "antenna_drive_range_az": ValueRange(0 << u.deg, 360 << u.deg),
        "antenna_drive_range_el": ValueRange(10 << u.deg, 90 << u.deg),
        "antenna_drive_warning_limit_az": ValueRange(10 << u.deg, 350 << u.deg),
        "antenna_drive_warning_limit_el": ValueRange(15 << u.deg, 80 << u.deg),
        "antenna_drive_critical_limit_az": ValueRange(5 << u.deg, 355 << u.deg),
        "antenna_drive_critical_limit_el": ValueRange(10 << u.deg, 85 << u.deg),
        "antenna_pointing_accuracy": 10 << u.arcsec,
        "ros_service_timeout_sec": 10,
    }
    expected_custom_config = {
        "observatory": "NANTEN2",
        "location": EarthLocation(
            lon="-67.70308139deg", lat="-22.96995611deg", height="4863.85m"
        ),
        "antenna_pid_param_az": [2.2, 0.0, 0.0],
        "antenna_pid_param_el": [2.2, 0.0, 0.0],
        "antenna_drive_range_az": ValueRange(-270 << u.deg, 270 << u.deg),
        "antenna_drive_range_el": ValueRange(0 << u.deg, 90 << u.deg),
        "antenna_drive_warning_limit_az": ValueRange(-240 << u.deg, 240 << u.deg),
        "antenna_drive_warning_limit_el": ValueRange(20 << u.deg, 80 << u.deg),
        "antenna_drive_critical_limit_az": ValueRange(-255 << u.deg, 255 << u.deg),
        "antenna_drive_critical_limit_el": ValueRange(5 << u.deg, 85 << u.deg),
        "antenna_pointing_accuracy": 3 << u.arcsec,
        "ros_service_timeout_sec": 10,
    }

    def test_no_config(self, dot_necst_dir: Path):
        assert not (dot_necst_dir / "config.toml").exists()
        config.reload()

        for k, expected in self.expected_default_config.items():
            try:
                eq = expected == getattr(config, k)
                assert eq if isinstance(eq, get_args(Boolean)) else all(eq)
            except ValueError:
                print("Couldn't determine equality of encapsulated sequence")
        assert not (dot_necst_dir / "config.toml").exists()

    def test_configure_no_config(self, dot_necst_dir: Path):
        assert not (dot_necst_dir / "config.toml").exists()
        configure()

        for k, expected in self.expected_default_config.items():
            try:
                eq = expected == getattr(config, k)
                assert eq if isinstance(eq, get_args(Boolean)) else all(eq)
            except ValueError:
                print("Couldn't determine equality of encapsulated sequence")
        assert (dot_necst_dir / "config.toml").exists()

    def test_configure_no_env(self, data_dir: Path, dot_necst_dir: Path):
        shutil.copyfile(
            data_dir / "sample_config_customized.toml", dot_necst_dir / "config.toml"
        )
        assert (dot_necst_dir / "config.toml").exists()
        config.reload()

        for k, expected in self.expected_custom_config.items():
            try:
                eq = expected == getattr(config, k)
                print(k, expected, getattr(config, k), eq)
                assert eq if isinstance(eq, get_args(Boolean)) else all(eq)
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
        config.reload()

        for k, expected in self.expected_custom_config.items():
            try:
                eq = expected == getattr(config, k)
                assert eq if isinstance(eq, get_args(Boolean)) else all(eq)
            except ValueError:
                print("Couldn't determine equality of encapsulated sequence")

        os.environ.pop("NECST_ROOT", None)
        config.reload()

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
        config.reload()

        for k, expected in self.expected_custom_config.items():
            try:
                eq = expected == getattr(config, k)
                # print(expected, getattr(config, k), eq)
                assert eq if isinstance(eq, get_args(Boolean)) else all(eq)
            except ValueError:
                print("Couldn't determine equality of encapsulated sequence")

        os.environ.pop("NECST_ROOT", None)
        config.reload()

    def test_flexible_lookup(self, dot_necst_dir: Path):
        assert not (dot_necst_dir / "config.toml").exists()
        os.environ.pop("NECST_ROOT", None)
        config.reload()

        assert (
            config.antenna_pid_param_az
            == self.expected_default_config["antenna_pid_param_az"]
        )
        assert (
            config.antenna_pid_param.az
            == self.expected_default_config["antenna_pid_param_az"]
        )

    def test_disallow_reserved_name(self, data_dir: Path, dot_necst_dir: Path):
        shutil.copyfile(
            data_dir / "invalid" / "config_reserved_name.toml",
            dot_necst_dir / "config.toml",
        )
        assert (dot_necst_dir / "config.toml").exists()
        with pytest.raises(ConfigurationError):
            config.reload()

        for k, expected in self.expected_default_config.items():
            try:
                eq = expected == getattr(config, k)
                assert eq if isinstance(eq, get_args(Boolean)) else all(eq)
            except ValueError:
                print("Couldn't determine equality of encapsulated sequence")

    def test_disallow_duplicated_definition(self, data_dir: Path, dot_necst_dir: Path):
        shutil.copyfile(
            data_dir / "invalid" / "config_duplicated_definition.toml",
            dot_necst_dir / "config.toml",
        )
        assert (dot_necst_dir / "config.toml").exists()
        with pytest.raises(ConfigurationError):
            config.reload()

        for k, expected in self.expected_default_config.items():
            try:
                eq = expected == getattr(config, k)
                assert eq if isinstance(eq, get_args(Boolean)) else all(eq)
            except ValueError:
                print("Couldn't determine equality of encapsulated sequence")

    def test_keys(self):
        assert set(config.keys()) > set(self.expected_default_config.keys())
        assert len(config.keys()) > 0

    def test_values(self):
        assert len(config.values()) == len(config.keys())
        for k, v in zip(config.keys(), config.values()):
            assert v == getattr(config, k)

    def test_items(self):
        assert len(config.items()) == len(config.keys())
        for (k, v), _k, _v in zip(config.items(), config.keys(), config.values()):
            assert k == _k
            assert v == _v

    def test_comparison(self):
        assert config.antenna == config.antenna
        assert config.antenna != config.dev
        assert config.antenna >= config.antenna
        assert config.antenna <= config.antenna
        assert config.antenna > config.antenna.pid
        assert config.antenna.pid < config.antenna
