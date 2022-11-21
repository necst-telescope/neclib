import pytest

from neclib.devices.motor import CPZ7415V


def get_cpz7415v():
    for inst in CPZ7415V._instances.values():
        if (inst.Model == CPZ7415V.Model) and (
            inst.Manufacturer == CPZ7415V.Manufacturer
        ):
            return inst


pytestmark = pytest.mark.skipif(
    get_cpz7415v() is None, reason="Config for CPZ7415V not found"
)


@pytest.fixture
def motor():
    return get_cpz7415v()


class TestCPZ7415V:
    def test_config_type(self, motor):
        motion_modes = (
            "jog",
            "org",
            "ptp",
            "timer",
            "single_step",
            "org_search",
            "org_exit",
            "org_zero",
            "ptp_repeat",
        )
        assert type(motor.rsw_id) is int
        assert type(motor.use_axes) is str
        assert all(x in "xyzu" for x in motor.use_axes)
        assert type(motor.motion) is dict
        assert type(motor.motion_mode) is dict
        assert all(ax in "xyzu" for ax in motor.motion.keys())
        assert type(motor.pulse_conf) is dict
        assert all(ax in "xyzu" for ax in motor.pulse_conf.keys())
        for axis in motor.use_axes:
            assert type(motor.motion[axis]) is dict
            assert set(motor.motion[axis].keys()) == {
                "clock",
                "acc_mode",
                "low_speed",
                "speed",
                "acc",
                "dec",
                "step",
            }
            assert type(motor.motion[axis]["clock"]) is int
            assert motor.motion[axis]["acc_mode"] in ("acc_normal", "acc_sin")
            assert type(motor.motion[axis]["low_speed"]) is int
            assert type(motor.motion[axis]["speed"]) is int
            assert type(motor.motion[axis]["acc"]) is int
            assert type(motor.motion[axis]["dec"]) is int
            assert type(motor.motion[axis]["step"]) is int
            assert motor.motion_mode[axis] in motion_modes
            assert type(motor.pulse_conf[axis]) is dict
            assert set(motor.pulse_conf[axis].keys()) == {
                "PULSE",
                "OUT",
                "DIR",
                "WAIT",
                "DUTY",
            }
            assert all(type(x) is int for x in motor.pulse_conf[axis].values())
        assert type(motor.speed_to_pulse_factor) in (int, float)
