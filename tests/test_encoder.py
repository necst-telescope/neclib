import astropy.units as u
import numpy as np

from neclib import utils
from neclib.simulator import AntennaEncoderEmulator

ENCODER_READ_INTERVAL = 0.1  # sec

kwargs = {
    "device_moment_of_inertia": [
        lambda az, el: (2500 + 3000 * np.cos(el)) * u.Unit("kg m2"),
        3000 * u.Unit("kg m2"),
    ],  # NANTEN2, rough estimation based on Ito (2005), Master's thesis.
    "motor_torque": [11.5 * u.Unit("N m"), 11.5 * u.Unit("N m")],
    # NANTEN2, from Ito (2005), Master's thesis.
    "angular_resolution": [
        360 * 3600 / (23600 * 400) * u.arcsec,
        360 * 3600 / (23600 * 400) * u.arcsec,
    ],  # RENISHAW RESM series encoder, which is installed in NANTEN2.,
}


class TestAntennaEncoderEmulator:
    def test_unit_independency(self):
        for unit in ["arcsec", "arcmin", "deg"]:
            # Conversion factors.
            deg_per_sec = utils.angle_conversion_factor("deg", unit)
            arcsec_per_sec = utils.angle_conversion_factor("arcsec", unit)

            speed = 0.5 * deg_per_sec

            AntennaEncoderEmulator.ANGLE_UNIT = unit
            enc = AntennaEncoderEmulator(**kwargs)
            enc.command(speed, "az")
            enc.command(speed, "el")

            for _ in range(50):
                # Hack the timer for fast-forwarding.
                enc.time = enc.time.map(lambda t: t - ENCODER_READ_INTERVAL)

                _ = enc.read()
            assert abs(enc.speed.az - speed) < 2 * arcsec_per_sec
            assert abs(enc.speed.el - speed) < 2 * arcsec_per_sec

    def test_initial_stability(self):
        enc = AntennaEncoderEmulator(**kwargs)
        arcsec = utils.angle_conversion_factor(enc.ANGLE_UNIT, "arcsec")
        log = []
        for _ in range(50):
            # Hack the timer for fast-forwarding.
            enc.time = enc.time.map(lambda t: t - ENCODER_READ_INTERVAL)

            log.append(enc.read())
        assert np.std([log_.az for log_ in log]) < 2 * arcsec
        assert np.std([log_.el for log_ in log]) < 2 * arcsec
        assert np.mean([log_.az for log_ in log]) - enc.position.az < 1 * arcsec
        assert np.mean([log_.el for log_ in log]) - enc.position.el < 1 * arcsec

    def test_speed_reach(self):
        deg = utils.angle_conversion_factor(AntennaEncoderEmulator.ANGLE_UNIT, "deg")
        for speed in [2 * deg, -2 * deg]:
            enc = AntennaEncoderEmulator(**kwargs)
            enc.command(speed, "az")
            enc.command(speed, "el")
            for _ in range(100):
                # Hack the timer for fast-forwarding.
                enc.time = enc.time.map(lambda t: t - ENCODER_READ_INTERVAL)

                _ = enc.read()
            assert enc.speed.az == speed
            assert enc.speed.el == speed

    def test_azel_independency(self):
        enc = AntennaEncoderEmulator(**kwargs)
        deg = utils.angle_conversion_factor(enc.ANGLE_UNIT, "deg")
        speed_az = 0.5 * deg
        speed_el = -0.3 * deg
        enc.command(speed_az, "az")
        enc.command(speed_el, "el")
        for _ in range(50):
            # Hack the timer for fast-forwarding.
            enc.time = enc.time.map(lambda t: t - ENCODER_READ_INTERVAL)
            _ = enc.read()
        assert enc.speed.az == speed_az
        assert enc.speed.el == speed_el

    def test_responce_delay(self):
        enc = AntennaEncoderEmulator(**kwargs)
        deg = utils.angle_conversion_factor(enc.ANGLE_UNIT, "deg")
        speed = 0.5 * deg
        enc.command(speed, "az")
        enc.command(speed, "el")
        for _ in range(10):
            assert enc.speed.az < speed
            assert enc.speed.el < speed

    def test_speed_change(self):
        enc = AntennaEncoderEmulator(**kwargs)
        deg = utils.angle_conversion_factor(enc.ANGLE_UNIT, "deg")
        speed_1 = 0.5 * deg
        enc.command(speed_1, "az")
        enc.command(speed_1, "el")
        for _ in range(50):
            # Hack the timer for fast-forwarding.
            enc.time = enc.time.map(lambda t: t - ENCODER_READ_INTERVAL)
            _ = enc.read()
        assert enc.speed.az == speed_1
        assert enc.speed.el == speed_1

        speed_2 = -0.3 * deg
        enc.command(speed_2, "az")
        enc.command(speed_2, "el")
        _ = enc.read()
        assert speed_1 > enc.speed.az > 0 > speed_2
        assert speed_1 > enc.speed.el > 0 > speed_2

        for _ in range(80):
            # Hack the timer for fast-forwarding.
            enc.time = enc.time.map(lambda t: t - ENCODER_READ_INTERVAL)
            _ = enc.read()
        assert enc.speed.az == speed_2
        assert enc.speed.el == speed_2
