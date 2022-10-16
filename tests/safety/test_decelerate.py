import astropy.units as u
import pytest

from neclib import utils
from neclib.safety import Decelerate


class TestDecelerate:
    def test_decelerate(self):
        guard = Decelerate(
            utils.ValueRange(-240 << u.deg, 240 << u.deg), 1 << u.Unit("deg/s^2")
        )
        assert guard(-240 << u.deg, -2 << u.deg / u.s).value == 0
        assert guard(-239 << u.deg, -1.5 << u.deg / u.s).value == pytest.approx(
            -1.4142135623730951
        )
        assert guard(200 << u.deg, 30 << u.deg / u.s).value == pytest.approx(
            8.94427190999916
        )
        assert guard(239 << u.deg, 30 << u.deg / u.s).value == pytest.approx(
            1.4142135623730951
        )

    def test_not_decelerate_reverse_direction(self):
        guard = Decelerate(
            utils.ValueRange(-240 << u.deg, 240 << u.deg), 0.1 << u.Unit("deg/s^2")
        )
        assert guard(-240 << u.deg, 2 << u.deg / u.s).value == 2
        assert guard(-239 << u.deg, 5 << u.deg / u.s).value == 5
        assert guard(200 << u.deg, -5 << u.deg / u.s).value == -5
        assert guard(239 << u.deg, -5 << u.deg / u.s).value == -5

    def test_preserve_input(self):
        guard = Decelerate(
            utils.ValueRange(-240 << u.deg, 240 << u.deg), 1.5 << u.Unit("deg/s^2")
        )
        assert guard(-239 << u.deg, -0.1 << u.deg / u.s).value == -0.1
        assert guard(-239 << u.deg, -1.4 << u.deg / u.s).value == -1.4
        assert guard(-230 << u.deg, -2 << u.deg / u.s).value == -2
        assert guard(0 << u.deg, -2 << u.deg / u.s).value == -2
        assert guard(0 << u.deg, 2 << u.deg / u.s).value == 2
        assert guard(230 << u.deg, 2 << u.deg / u.s).value == 2
        assert guard(239.5 << u.deg, 0.1 << u.deg / u.s).value == 0.1

    def test_out_of_range(self):
        guard = Decelerate(
            utils.ValueRange(-240 << u.deg, 240 << u.deg), 1.5 << u.Unit("deg/s^2")
        )
        assert guard(-241 << u.deg, -2 << u.deg / u.s).value == 0
        assert guard(-241 << u.deg, 2 << u.deg / u.s).value == 0
        assert guard(241 << u.deg, -2 << u.deg / u.s).value == 0
        assert guard(241 << u.deg, 2 << u.deg / u.s).value == 0
        assert guard(-270 << u.deg, -2 << u.deg / u.s).value == 0
        assert guard(270 << u.deg, 2 << u.deg / u.s).value == 0

    def test_accept_float_input(self):
        guard = Decelerate(
            utils.ValueRange(-240 << u.deg, 240 << u.deg), 1.5 << u.Unit("deg/s^2")
        )
        assert guard(-240, -2, u.deg).value == 0
        assert guard(-239.5, -0.1, "deg").value == -0.1
        assert guard(239 << u.deg, -300, "arcmin").to_value("arcmin/s") == -300
        assert guard(18000, 120 << u.arcmin / u.s, "arcmin").value == 0
