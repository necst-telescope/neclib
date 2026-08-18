import tomllib
from pathlib import Path
from types import SimpleNamespace

import neclib

from neclib.devices.spectrometer.simulator import SpectrometerSimulator


def test_spectrometer_simulator_packet_format():
    spectrometer = SpectrometerSimulator()
    spectrometer.change_spec_ch(2**15)
    timestamp, time_spectrometer, data = spectrometer.get_spectra()

    assert isinstance(timestamp, float)
    assert time_spectrometer == str(timestamp)
    assert list(data) == [0]
    assert isinstance(data[0], list)
    assert len(data[0]) == 2**15


def test_spectrometer_simulator_uses_configured_boards():
    spectrometer = SpectrometerSimulator()
    original_config = SpectrometerSimulator.Config
    SpectrometerSimulator.Config = SimpleNamespace(
        bw_MHz={"1": 2500, "2": 2500, "3": 2500, "4": 2500}
    )

    try:
        _, _, data = spectrometer.get_spectra()
        assert list(data) == [1, 2, 3, 4]
        assert all(len(spectrum) == 2**15 for spectrum in data.values())
    finally:
        SpectrometerSimulator.Config = original_config


def test_spectrometer_simulator_channel_binning():
    spectrometer = SpectrometerSimulator()
    try:
        spectrometer.change_spec_ch(1024)
        _, _, data = spectrometer.get_spectra()
        assert all(len(spectrum) == 1024 for spectrum in data.values())
    finally:
        spectrometer.change_spec_ch(2**15)


def test_default_simulator_config_enables_spectrometer():
    config_path = Path(neclib.__file__).parent / "defaults" / "simulator_config.toml"
    with config_path.open("rb") as file:
        simulator_config = tomllib.load(file)

    assert simulator_config["simulator"] is True
    assert simulator_config["spectrometer"]["xffts"]["_"] == "XFFTS"
    assert simulator_config["spectrometer"]["xffts"]["max_ch"] == 2**15
