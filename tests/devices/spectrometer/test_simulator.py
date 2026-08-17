import tomllib
from pathlib import Path

import neclib

from neclib.devices.spectrometer.simulator import SpectrometerSimulator


def test_spectrometer_simulator_packet_format():
    timestamp, time_spectrometer, data = SpectrometerSimulator().get_spectra()

    assert isinstance(timestamp, float)
    assert time_spectrometer == str(timestamp)
    assert list(data) == [0]
    assert isinstance(data[0], list)
    assert len(data[0]) == 2**15


def test_default_simulator_config_enables_spectrometer():
    config_path = Path(neclib.__file__).parent / "defaults" / "simulator_config.toml"
    with config_path.open("rb") as file:
        simulator_config = tomllib.load(file)

    assert simulator_config["simulator"] is True
    assert simulator_config["spectrometer"]["xffts"]["_"] == "XFFTS"
    assert simulator_config["spectrometer"]["xffts"]["max_ch"] == 2**15
