import shutil
from pathlib import Path
from unittest.mock import patch

import astropy.units as u
import numpy as np
import pytest
from astropy.coordinates import EarthLocation

from neclib import NECSTConfigurationError, config, configure
from neclib.core import ValueRange

from ..conftest import tmp_environ

Boolean = (bool, np.bool_)


@pytest.fixture
def mock_home_dir(tmp_path_factory):
    home = tmp_path_factory.mktemp("username")
    default_necst_root = "neclib.core.configuration.DefaultNECSTRoot"
    with patch("pathlib.Path.home", return_value=home), patch(
        default_necst_root, home / ".necst"
    ):
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
        "antenna.pid_param_az": [0.8, 0.0, 0.0],
        "antenna.pid_param_el": [0.8, 0.0, 0.0],
        "antenna.drive_range_az": ValueRange(0 << u.deg, 360 << u.deg),
        "antenna.drive_range_el": ValueRange(10 << u.deg, 90 << u.deg),
        "antenna.drive_warning_limit_az": ValueRange(10 << u.deg, 350 << u.deg),
        "antenna.drive_warning_limit_el": ValueRange(20 << u.deg, 80 << u.deg),
        "antenna.drive_critical_limit_az": ValueRange(5 << u.deg, 355 << u.deg),
        "antenna.drive_critical_limit_el": ValueRange(15 << u.deg, 85 << u.deg),
        "antenna.pointing_accuracy": 10 << u.arcsec,
        "ros.service_timeout_sec": 10,
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

    def test_no_config(self, dot_necst_dir: Path) -> None:
        assert not (dot_necst_dir / "config.toml").exists()
        config.reload()

        for k, expected in self.expected_default_config.items():
            try:
                actual = getattr(config, k)
                eq = expected == actual
                _err_msg = f"{k} ({expected=}, {actual=})"
                assert eq if isinstance(eq, Boolean) else all(eq), _err_msg
            except ValueError:
                print("Couldn't determine equality of encapsulated sequence")
        assert not (dot_necst_dir / "config.toml").exists()

    def test_configure_no_config(self, dot_necst_dir: Path) -> None:
        assert not (dot_necst_dir / "config.toml").exists()
        configure()

        for k, expected in self.expected_default_config.items():
            try:
                eq = expected == getattr(config, k)
                assert eq if isinstance(eq, Boolean) else all(eq)
            except ValueError:
                print("Couldn't determine equality of encapsulated sequence")
        assert (dot_necst_dir / "config.toml").exists()

    def test_configure_no_env(self, data_dir: Path, dot_necst_dir: Path) -> None:
        shutil.copyfile(
            data_dir / "sample_config_customized.toml", dot_necst_dir / "config.toml"
        )
        assert (dot_necst_dir / "config.toml").exists()
        config.reload()

        for k, expected in self.expected_custom_config.items():
            try:
                eq = expected == getattr(config, k)
                print(k, expected, getattr(config, k), eq)
                assert eq if isinstance(eq, Boolean) else all(eq)
            except ValueError:
                print("Couldn't determine equality of encapsulated sequence")

    def test_configure_with_env_but_no_config(
        self, data_dir: Path, dot_necst_dir: Path, custom_necst_root_dir: Path
    ) -> None:
        with tmp_environ(NECST_ROOT=str(custom_necst_root_dir)):
            shutil.copyfile(
                data_dir / "sample_config_customized.toml",
                dot_necst_dir / "config.toml",
            )
            assert (dot_necst_dir / "config.toml").exists()
            assert not (custom_necst_root_dir / "config.toml").exists()
            config.reload()

            for k, expected in self.expected_custom_config.items():
                try:
                    eq = expected == getattr(config, k)
                    assert eq if isinstance(eq, Boolean) else all(eq)
                except ValueError:
                    print("Couldn't determine equality of encapsulated sequence")

        config.reload()

    def test_configure_with_env(
        self, data_dir: Path, dot_necst_dir: Path, custom_necst_root_dir: Path
    ) -> None:
        with tmp_environ(NECST_ROOT=str(custom_necst_root_dir)):
            shutil.copyfile(
                data_dir / "sample_config_customized.toml",
                custom_necst_root_dir / "config.toml",
            )
            shutil.copyfile(
                data_dir / "sample_config.toml", dot_necst_dir / "config.toml"
            )
            assert (custom_necst_root_dir / "config.toml").exists()
            assert (dot_necst_dir / "config.toml").exists()
            config.reload()

            for k, expected in self.expected_custom_config.items():
                try:
                    eq = expected == getattr(config, k)
                    assert eq if isinstance(eq, Boolean) else all(eq)
                except ValueError:
                    print("Couldn't determine equality of encapsulated sequence")

        config.reload()

    def test_flexible_lookup(self, dot_necst_dir: Path) -> None:
        assert not (dot_necst_dir / "config.toml").exists()
        with tmp_environ(NECST_ROOT=""):
            config.reload()

            assert (
                config.antenna.pid.param_az
                == self.expected_default_config["antenna.pid_param_az"]
            )
            assert (
                config.antenna.pid_param_az
                == self.expected_default_config["antenna.pid_param_az"]
            )

            assert config.antenna_command.frequency == 50

    def test_disallow_reserved_name(self, data_dir: Path, dot_necst_dir: Path) -> None:
        shutil.copyfile(
            data_dir / "invalid" / "config_reserved_name.toml",
            dot_necst_dir / "config.toml",
        )
        assert (dot_necst_dir / "config.toml").exists()
        with pytest.raises(NECSTConfigurationError):
            config.reload()

        for k, expected in self.expected_default_config.items():
            try:
                eq = expected == getattr(config, k)
                assert eq if isinstance(eq, Boolean) else all(eq)
            except ValueError:
                print("Couldn't determine equality of encapsulated sequence")

    def test_disallow_duplicated_definition(
        self, data_dir: Path, dot_necst_dir: Path
    ) -> None:
        shutil.copyfile(
            data_dir / "invalid" / "config_duplicated_definition.toml",
            dot_necst_dir / "config.toml",
        )
        assert (dot_necst_dir / "config.toml").exists()
        with pytest.raises(NECSTConfigurationError):
            config.reload()

        for k, expected in self.expected_default_config.items():
            try:
                eq = expected == getattr(config, k)
                assert eq if isinstance(eq, Boolean) else all(eq)
            except ValueError:
                print("Couldn't determine equality of encapsulated sequence")

    def test_keys(self):
        assert set(config.keys()) > set(self.expected_default_config.keys())
        assert len(config.keys()) > 0

    def test_values(self):
        assert len(config.values()) == len(config.keys())
        for k, v in zip(config.keys(), config.values()):
            assert v == config[k]

    def test_items(self):
        assert len(config.items()) == len(config.keys())
        for (k, v), _k, _v in zip(config.items(), config.keys(), config.values()):
            assert k == _k
            assert v == _v

    def test_comparison(self):
        assert config.antenna == config.antenna
        assert config.antenna != config.antenna.pid
        assert config.antenna >= config.antenna
        assert config.antenna <= config.antenna
        assert config.antenna > config.antenna.pid
        assert config.antenna.pid < config.antenna

    def test_addition(self):
        merged = config.antenna_motor + config.chopper_motor
        assert merged.rsw_id == 0
        assert merged.position["insert"] == 4750
        assert merged.useaxes == "xyu"
        assert merged.x.pulse_conf["PULSE"] == 1
        assert type(merged.x.pulse_conf["PULSE"]) is int
        assert type(merged.x.pulse_conf) is dict
