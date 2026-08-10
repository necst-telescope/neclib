from neclib.devices.spectrometer.simulator import SpectrometerSimulator


def test_spectrometer_simulator_packet_format():
    timestamp, time_spectrometer, data = SpectrometerSimulator().get_spectra()

    assert isinstance(timestamp, float)
    assert time_spectrometer == str(timestamp)
    assert list(data) == [0]
    assert len(data[0]) == 2**15
