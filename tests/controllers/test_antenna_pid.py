import numpy as np

from neclib import utils
from neclib.controllers import PIDController
from neclib.typing import AngleUnit


PID_CALC_INTERVAL = 0.1  # sec


def encoder_emulator(
    current_coord: float, speed: float, unit: AngleUnit = "deg"
) -> float:
    """Encoder emulator, response delay isn't taken into account."""
    proceeded = speed * PID_CALC_INTERVAL  # Assume PID calculation executed every 0.1s.
    fluctuation = 1 * np.random.randn() * utils.angle_conversion_factor("arcsec", unit)
    return current_coord + proceeded + fluctuation


class TestPIDController:
    def test_unit_independency(self):
        for unit in ["arcsec", "arcmin", "deg"]:
            # Conversion factors.
            deg = utils.angle_conversion_factor("deg", unit)
            arcsec = utils.angle_conversion_factor("arcsec", unit)

            target = 50 * deg
            current_coord = 30 * deg
            speed = 0

            PIDController.ANGLE_UNIT = unit
            controller = PIDController(pid_param=[2, 0, 0])

            for _ in range(145):
                # Hack the controller timer for fast-forwarding.
                controller.time = controller.time.map(
                    lambda t: np.nan if np.isnan(t) else t - PID_CALC_INTERVAL
                )

                current_coord = encoder_emulator(current_coord, speed, unit)
                speed = controller.get_speed(target, current_coord)
            assert abs(current_coord - target) < 5 * arcsec

    def test_speed_limit(self):
        target = 50
        current_coord = 30
        speed = 0
        controller = PIDController()
        for _ in range(100):
            # Hack the controller timer for fast-forwarding.
            controller.time = controller.time.map(
                lambda t: np.nan if np.isnan(t) else t - PID_CALC_INTERVAL
            )

            current_coord = encoder_emulator(current_coord, speed, "deg")
            speed = controller.get_speed(target, current_coord)
            assert abs(speed) <= controller.max_speed

    def test_acceleration_limit(self):
        target = 50
        current_coord = 30
        speed = 0
        controller = PIDController()
        for _ in range(100):
            # Hack the controller timer for fast-forwarding.
            controller.time = controller.time.map(
                lambda t: np.nan if np.isnan(t) else t - PID_CALC_INTERVAL
            )

            current_coord = encoder_emulator(current_coord, speed, "deg")
            _speed = speed
            speed = controller.get_speed(target, current_coord)
            acceleration = (speed - _speed) / controller.dt
            assert abs(acceleration) <= controller.max_acceleration

    def test_unit_independent_limiting(self):
        for unit in ["arcsec", "arcmin", "deg"]:
            # Conversion factors.
            deg = utils.angle_conversion_factor("deg", unit)

            target = 50 * deg
            current_coord = 30 * deg
            speed = 0

            PIDController.ANGLE_UNIT = unit
            controller = PIDController(pid_param=[2, 0, 0])

            for _ in range(100):
                # Hack the controller timer for fast-forwarding.
                controller.time = controller.time.map(
                    lambda t: np.nan if np.isnan(t) else t - PID_CALC_INTERVAL
                )

                current_coord = encoder_emulator(current_coord, speed, unit)
                _speed = speed
                speed = controller.get_speed(target, current_coord)
                acceleration = (speed - _speed) / controller.dt
                print(speed, acceleration)

                _e = 1e-8
                # ``_e`` is a workaround for error caused by floating point overflow.
                assert abs(speed) <= controller.max_speed + _e
                assert abs(acceleration) <= controller.max_acceleration + _e

    def test_stop(self):
        for _ in range(10):
            assert PIDController().get_speed(50, 10, stop=True) == 0
