import tomllib
from pathlib import Path
from types import SimpleNamespace

import neclib
import numpy as np
import pytest

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
        spectrometer.set_on_source(False)
        _, _, sky_data = spectrometer.get_spectra()
        sky_power = float(np.nansum(sky_data[1]))

        spectrometer.set_hot(True)
        _, _, hot_data = spectrometer.get_spectra()
        hot_power = float(np.nansum(hot_data[1]))

        expected = (150.0 + 293.0) / (150.0 + 70.0)
        assert np.isclose(spectrometer.hot_factor, expected)
        assert np.isclose(hot_power / sky_power, expected, rtol=0.01)
    finally:
        spectrometer.set_hot(False)
        SpectrometerSimulator.Config = original_config


def test_spectrometer_simulator_on_adds_gaussian_line_only_when_enabled():
    spectrometer = SpectrometerSimulator()
    original_config = SpectrometerSimulator.Config
    SpectrometerSimulator.Config = SimpleNamespace(bw_MHz={"1": 2500})

    velocity_axis = np.linspace(-100.0, 100.0, 2**15)
    center = float(velocity_axis[1000])
    old_white_noise = spectrometer._white_noise_fraction
    old_gain_step = spectrometer._gain_step_sigma
    try:
        spectrometer._white_noise_fraction = 0.0
        spectrometer._gain_step_sigma = 0.0
        spectrometer._gain = 1.0
        spectrometer._board_scale = {1: 1.0}
        spectrometer.set_hot(False)
        spectrometer.set_on_line_components(
            {
                1: [
                    {
                        "velocity_axis_kms": velocity_axis,
                        "v_center_kms": center,
                        "fwhm_kms": 10.0,
                        "t_line_peak_K": 22.0,
                    }
                ]
            }
        )

        spectrometer.set_on_source(False)
        _, _, off_data = spectrometer.get_spectra()
        spectrometer.set_on_source(True)
        _, _, on_data = spectrometer.get_spectra()

        off = np.asarray(off_data[1])
        on = np.asarray(on_data[1])
        expected_peak_ratio = 1.0 + 22.0 / (150.0 + 70.0)

        assert np.isclose(on[1000] / off[1000], expected_peak_ratio)
        assert np.isclose(on[-1] / off[-1], 1.0)
    finally:
        spectrometer.set_on_source(False)
        spectrometer.set_on_line_components({})
        spectrometer._white_noise_fraction = old_white_noise
        spectrometer._gain_step_sigma = old_gain_step
        SpectrometerSimulator.Config = original_config


def test_spectrometer_simulator_supports_multiple_lines_on_same_board():
    spectrometer = SpectrometerSimulator()
    original_config = SpectrometerSimulator.Config
    SpectrometerSimulator.Config = SimpleNamespace(bw_MHz={"1": 2500})

    velocity_axis = np.linspace(-100.0, 100.0, 2**15)
    center1 = float(velocity_axis[1000])
    center2 = float(velocity_axis[2000])
    old_white_noise = spectrometer._white_noise_fraction
    old_gain_step = spectrometer._gain_step_sigma
    try:
        spectrometer._white_noise_fraction = 0.0
        spectrometer._gain_step_sigma = 0.0
        spectrometer._gain = 1.0
        spectrometer._board_scale = {1: 1.0}
        spectrometer.set_hot(False)
        spectrometer.set_on_line_components(
            {
                1: [
                    {
                        "velocity_axis_kms": velocity_axis,
                        "v_center_kms": center1,
                        "fwhm_kms": 1.0,
                        "t_line_peak_K": 20.0,
                    },
                    {
                        "velocity_axis_kms": velocity_axis,
                        "v_center_kms": center2,
                        "fwhm_kms": 1.0,
                        "t_line_peak_K": 5.0,
                    },
                ]
            }
        )
        spectrometer.set_on_source(True)

        _, _, data = spectrometer.get_spectra()
        spectrum = np.asarray(data[1])
        baseline = spectrometer._baseline

        assert spectrum[1000] > baseline
        assert spectrum[2000] > baseline
        assert spectrum[1000] > spectrum[2000]
    finally:
        spectrometer.set_on_source(False)
        spectrometer.set_on_line_components({})
        spectrometer._white_noise_fraction = old_white_noise
        spectrometer._gain_step_sigma = old_gain_step
        SpectrometerSimulator.Config = original_config


def test_spectrometer_simulator_hot_suppresses_on_line():
    spectrometer = SpectrometerSimulator()
    original_config = SpectrometerSimulator.Config
    SpectrometerSimulator.Config = SimpleNamespace(bw_MHz={"1": 2500})

    velocity_axis = np.linspace(-100.0, 100.0, 2**15)
    center = float(velocity_axis[1000])
    old_white_noise = spectrometer._white_noise_fraction
    old_gain_step = spectrometer._gain_step_sigma
    try:
        spectrometer._white_noise_fraction = 0.0
        spectrometer._gain_step_sigma = 0.0
        spectrometer._gain = 1.0
        spectrometer._board_scale = {1: 1.0}
        spectrometer.set_on_line_components(
            {
                1: [
                    {
                        "velocity_axis_kms": velocity_axis,
                        "v_center_kms": center,
                        "fwhm_kms": 10.0,
                        "t_line_peak_K": 100.0,
                    }
                ]
            }
        )
        spectrometer.set_on_source(True)
        spectrometer.set_hot(True)

        _, _, data = spectrometer.get_spectra()
        spectrum = np.asarray(data[1])

        assert np.isclose(spectrum[1000], spectrum[-1])
    finally:
        spectrometer.set_hot(False)
        spectrometer.set_on_source(False)
        spectrometer.set_on_line_components({})
        spectrometer._white_noise_fraction = old_white_noise
        spectrometer._gain_step_sigma = old_gain_step
        SpectrometerSimulator.Config = original_config


def test_spectrometer_simulator_rejects_invalid_line_component():
    spectrometer = SpectrometerSimulator()
    velocity_axis = np.linspace(-100.0, 100.0, 2**15)

    with pytest.raises(ValueError, match="fwhm_kms"):
        spectrometer.set_on_line_components(
            {
                1: [
                    {
                        "velocity_axis_kms": velocity_axis,
                        "v_center_kms": 0.0,
                        "fwhm_kms": 0.0,
                        "t_line_peak_K": 10.0,
                    }
                ]
            }
        )


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
