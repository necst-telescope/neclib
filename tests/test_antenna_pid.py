import numpy as np

from necst_lib import PIDController, utils
from necst_lib.typing import AngleUnit


def encoder_emulator(
    current_coord: float, speed: float, unit: AngleUnit = "deg"
) -> float:
    """Encoder emulator, no response delay took into account."""
    proceeded = speed * 0.1  # Assume PID calculation executed every 0.1s.
    fluctuation = 1 * np.random.randn() * utils.angle_conversion_factor("arcsec", unit)
    return current_coord + proceeded + fluctuation


class TestPIDController:
    def test_unit_independency(self):
        for unit in ["deg", "arcmin", "arcsec"]:
            factor_from_deg = utils.angle_conversion_factor("deg", unit)
            target = 50 * factor_from_deg
            current_coord = 30 * factor_from_deg
            speed = 0
            scaled_threshold = {
                k: v * factor_from_deg for k, v in PIDController.THRESHOLD.items()
            }
            controller = PIDController(
                pid_param=[2, 0, 0],
                max_speed=PIDController.MAX_SPEED * factor_from_deg,
                max_acceleration=PIDController.MAX_ACCELERATION * factor_from_deg,
                threshold=scaled_threshold,
            )
            controller.ANGLE_UNIT = unit

            for _ in range(140):
                # Hack the controller timer for fast-forwarding.
                controller.time = [
                    np.nan if np.isnan(t) else t - 0.1 for t in controller.time
                ]

                current_coord = encoder_emulator(current_coord, speed, unit)
                speed = controller.get_speed(target, current_coord)
            factor_from_arcsec = utils.angle_conversion_factor("arcsec", unit)
            assert abs(current_coord - target) < 5 * factor_from_arcsec

    def test_speed_limit(self):
        target = 50
        current_coord = 30
        speed = 0
        controller = PIDController()
        for _ in range(100):
            # Hack the controller timer for fast-forwarding.
            controller.time = [
                np.nan if np.isnan(t) else t - 0.1 for t in controller.time
            ]

            current_coord = encoder_emulator(current_coord, speed, "deg")
            speed = controller.get_speed(target, current_coord)
            assert abs(speed) <= controller.MAX_SPEED

    def test_acceleration_limit(self):
        target = 50
        current_coord = 30
        speed = 0
        controller = PIDController()
        for _ in range(100):
            # Hack the controller timer for fast-forwarding.
            controller.time = [
                np.nan if np.isnan(t) else t - 0.1 for t in controller.time
            ]

            current_coord = encoder_emulator(current_coord, speed, "deg")
            _speed = speed
            speed = controller.get_speed(target, current_coord)
            acceleration = (speed - _speed) / controller.dt
            assert abs(acceleration) <= controller.MAX_ACCELERATION

    def test_stop(self):
        for _ in range(10):
            assert PIDController().get_speed(50, 10, stop=True) == 0

    def test_optimum_angle(self):
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
            assert PIDController.optimum_angle(**kwargs) in ans
