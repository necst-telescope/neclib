import tomllib
from pathlib import Path
from types import SimpleNamespace

import neclib
import numpy as np

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


def test_spectrometer_simulator_total_power_varies_over_time():
    spectrometer = SpectrometerSimulator()
    original_config = SpectrometerSimulator.Config
    SpectrometerSimulator.Config = SimpleNamespace(bw_MHz={"1": 2500})

    # Keep this regression test deterministic while exercising the same random model.
    spectrometer._rng = np.random.default_rng(0)
    spectrometer._gain = 1.0
    spectrometer._board_scale = {}

    try:
        total_powers = []
        for _ in range(5):
            _, _, data = spectrometer.get_spectra()
            total_powers.append(np.float32(np.nansum(data[1])))

        assert len(set(total_powers)) > 1
    finally:
        SpectrometerSimulator.Config = original_config


def test_spectrometer_simulator_hot_load_scales_broadband_power():
    original_config = SpectrometerSimulator.Config
    SpectrometerSimulator.Config = SimpleNamespace(
        bw_MHz={"1": 2500},
        simulator_t_rx_K=150.0,
        simulator_t_sky_K=70.0,
        simulator_t_hot_K=293.0,
    )

    try:
        spectrometer = SpectrometerSimulator()
        spectrometer._rng = np.random.default_rng(0)
        spectrometer._gain_step_sigma = 0.0
        spectrometer._board_scale = {1: 1.0}

        spectrometer.set_hot(False)
        _, _, sky_data = spectrometer.get_spectra()
        sky_power = float(np.nansum(sky_data[1]))

        spectrometer.set_hot(True)
        _, _, hot_data = spectrometer.get_spectra()
        hot_power = float(np.nansum(hot_data[1]))

        expected = (150.0 + 293.0) / (150.0 + 70.0)
        assert np.isclose(spectrometer.hot_factor, expected)
        assert np.isclose(hot_power / sky_power, expected, rtol=0.01)
    finally:
        SpectrometerSimulator.Config = original_config


def test_default_simulator_config_enables_spectrometer():
    config_path = Path(neclib.__file__).parent / "defaults" / "simulator_config.toml"
    with config_path.open("rb") as file:
        simulator_config = tomllib.load(file)

    assert simulator_config["simulator"] is True
    xffts = simulator_config["spectrometer"]["xffts"]
    assert xffts["_"] == "XFFTS"
    assert xffts["max_ch"] == 2**15
    assert xffts["simulator_t_rx_K"] == 150.0
    assert xffts["simulator_t_sky_K"] == 70.0
    assert xffts["simulator_t_hot_K"] == 293.0
