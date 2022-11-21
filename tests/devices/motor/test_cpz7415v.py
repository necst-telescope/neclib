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
        assert type(motor.Config.rsw_id) is int
        assert type(motor.Config.useaxes) is str
        assert all(x in "xyzu" for x in motor.Config.useaxes)
        for axis in motor.Config.useaxes:
            assert type(getattr(motor.Config, f"{axis}_mode")) is str
            assert getattr(motor.Config, f"{axis}_mode") in motion_modes
            assert type(getattr(motor.Config, f"{axis}_pulse_conf")) is dict
            assert set(getattr(motor.Config, f"{axis}_pulse_conf").keys()) == {
                "PULSE",
                "OUT",
                "DIR",
                "WAIT",
                "DUTY",
            }
            assert all(
                type(x) is int
                for x in getattr(motor.Config, f"{axis}_pulse_conf").values()
            )
            assert type(getattr(motor.Config, f"{axis}_motion_clock")) is int
            assert type(getattr(motor.Config, f"{axis}_motion_acc_mode")) is str
            assert getattr(motor.Config, f"{axis}_motion_acc_mode") in (
                "acc_normal",
                "acc_sin",
            )
            assert type(getattr(motor.Config, f"{axis}_motion_low_speed")) is int
            assert type(getattr(motor.Config, f"{axis}_motion_speed")) is int
            assert type(getattr(motor.Config, f"{axis}_motion_acc")) is int
            assert type(getattr(motor.Config, f"{axis}_motion_dec")) is int
            assert type(getattr(motor.Config, f"{axis}_motion_step")) is int
        assert all(x in "xyzu" for x in motor.Config.axis.values())
        assert type(motor.Config.speed_to_pulse_factor) in (int, float)
