import astropy.units as u

from neclib.coordinates import DriveLimitChecker


class TestDriveLimitChecker:
    def test_single_choice(self):
        checker = DriveLimitChecker(
            [5 << u.deg, 355 << u.deg], [10 << u.deg, 350 << u.deg]
        )
        assert checker.optimize(15 << u.deg, 200 << u.deg) == 200 << u.deg

    def test_multiple_choice(self):
        checker = DriveLimitChecker(
            [-260 << u.deg, 260 << u.deg], [-250 << u.deg, 250 << u.deg]
        )
        assert checker.optimize(15 << u.deg, 200 << u.deg) == -160 << u.deg

    def test_extremely_wide_drive_range(self):
        checker = DriveLimitChecker(
            [-36000 << u.deg, 36000 << u.deg], [-36000 << u.deg, 36000 << u.deg]
        )
        assert checker.optimize(18000 << u.deg, 30 << u.deg) == 18030 << u.deg

    def test_avoid_target_near_limit(self):
        checker = DriveLimitChecker(
            [-260 << u.deg, 260 << u.deg], [-250 << u.deg, 250 << u.deg]
        )
        assert checker.optimize(240 << u.deg, 251 << u.deg) == -109 << u.deg

    def test_dont_avoid_target_near_limit_during_observation(self):
        checker = DriveLimitChecker(
            [-260 << u.deg, 260 << u.deg], [-250 << u.deg, 250 << u.deg]
        )
        assert checker.optimize(249 << u.deg, 251 << u.deg) == 251 << u.deg

    def test_no_error_equally_preferable_candidates(self):
        checker = DriveLimitChecker(
            [-260 << u.deg, 260 << u.deg], [-250 << u.deg, 250 << u.deg]
        )
        result = checker.optimize(0 << u.deg, 180 << u.deg)
        assert (result == -180 << u.deg) or (result == 180 << u.deg)

    def test_mixed_units(self):
        checker = DriveLimitChecker(
            [-260 << u.deg, 260 << u.deg], [-15000 << u.arcmin, 15000 << u.arcmin]
        )
        assert checker.optimize(15 << u.deg, 720000 << u.arcsec) == -160 << u.deg

    def test_float_input(self):
        checker = DriveLimitChecker([-260, 260], [-250, 250], unit="deg")
        assert checker.optimize(15, 200, unit="deg") == -160 << u.deg

    def test_large_observation_size(self):
        checker = DriveLimitChecker(
            [-260 << u.deg, 260 << u.deg],
            [-250 << u.deg, 250 << u.deg],
            max_observation_size=15 << u.deg,
        )
        assert checker.optimize(240 << u.deg, 251 << u.deg) == 251 << u.deg
