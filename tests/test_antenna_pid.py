import numpy as np

from neclib import optimum_angle, PIDController, utils
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


def test_optimum_angle():
    keys = ["current", "target", "limits", "margin", "unit"]
    args = [
        # If there's no choice but to drive >180deg, do so.
        ([15, 200, [0, 360], 5, "deg"], [200]),
        # If there're multiple choices, select shorter path.
        ([15, 200, [-270, 270], 20, "deg"], [-160]),
        # Even if up to 100 turns are accepted.
        ([18000, 30, [-36000, 36000], 20, "deg"], [18030]),
        # Avoid driving into coords close to limits.
        ([240, 260, [-270, 270], 20, "deg"], [-100]),
        # Except in the case the target is within 5deg from current coord.
        ([265, 266, [-270, 270], 20, "deg"], [266]),
        # If there's two equally acceptable candidates, return either of them.
        ([0, 180, [-270, 270], 20, "deg"], [-180, 180]),
        # Of cause in other units.
        ([900, 12000, [-16200, 16200], 1200, "arcmin"], [-9600]),
        ([54000, 720000, [-972000, 972000], 72000, "arcsec"], [-576000]),
    ]
    test_cases = [({k: v for k, v in zip(keys, arg)}, ans) for arg, ans in args]

    for kwargs, ans in test_cases:
        assert optimum_angle(**kwargs) in ans
