import pytest

from neclib.devices.motor import CPZ7415V

from ..conftest import get_instance

pytestmark = pytest.mark.skipif(
    get_instance(CPZ7415V) is None, reason="CPZ7415V is not configured"
)


class TestCPZ7415V:
    def test_config_type(self):
        motor = get_instance(CPZ7415V)
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
        for ax, factor in motor.Config.speed_to_pulse_factor.items():
            assert ax in "xyzu"
            assert type(factor) in (int, float)
