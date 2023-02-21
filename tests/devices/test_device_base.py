from abc import abstractmethod
from typing import Any

import pytest

from neclib import devices
from neclib.devices.device_base import DeviceBase, Devices

from ..conftest import configured_tester_factory


class Motor(DeviceBase):
    @abstractmethod
    def get_id(self) -> int:
        ...


class MotorModel1(Motor):
    Model = "MotorModel1"
    Manufacturer = "???"
    Identifier = "switch1"

    def get_id(self) -> int:
        return 1

    def ident(self, id: Any) -> Any:
        return id

    def finalize(self) -> None:
        pass


class MotorModel2(Motor):
    Model = "MotorModel2"
    Manufacturer = "???"
    Identifier = "switch1"

    def get_id(self) -> int:
        return 2

    def ident(self, id: Any) -> Any:
        return id

    def finalize(self) -> None:
        pass


class MotorModel3(Motor):
    Model = "MotorModel3"
    Manufacturer = "???"
    Identifier = "switch1"

    counter: int = 0

    def __init__(self) -> None:
        self.__class__.counter += 1

    def get_id(self) -> int:
        return 3

    def ident(self, id: Any) -> Any:
        return id

    def finalize(self) -> None:
        pass


class MotorModel4(Motor):
    Model = "MotorModel4"
    Manufacturer = "???"
    Identifier = "switch1"
    is_simulator = True

    def get_id(self) -> int:
        return 4

    def ident(self, id: Any) -> Any:
        return id

    def finalize(self) -> None:
        pass


class TestDeviceBase(configured_tester_factory("config_devices")):
    @classmethod
    def setup_class(cls) -> None:
        super().setup_class()
        devices.reload()

    @classmethod
    def teardown_class(cls) -> None:
        super().teardown_class()
        devices.reload()

    def test_config_parsing(self) -> None:
        inst = devices.MyMotor1()  # type: ignore
        assert isinstance(inst, Devices)
        assert isinstance(inst[None], MotorModel1)
        assert inst.Config.switch1 == 5

        cls = devices.MyMotor2  # type: ignore
        inst = cls()
        assert isinstance(inst, Devices)
        assert isinstance(inst[None], MotorModel2)
        assert inst.Config.switch1 == 5

    def test_same_instance_for_same_identity(self) -> None:
        MyMotor1 = DeviceBase.bind("my_motor_1", "motor_model_1")
        inst1 = MyMotor1()
        assert isinstance(inst1, MotorModel1)

        MyMotor3 = DeviceBase.bind("my_motor_3", "motor_model_1")
        inst2 = MyMotor3()
        assert isinstance(inst2, MotorModel1)

        assert inst1 is inst2

    def test_different_instance_for_different_identity(self) -> None:
        MyMotor1 = DeviceBase.bind("my_motor_1", "motor_model_1")
        inst1 = MyMotor1()
        assert inst1.Config.switch1 == 5  # type: ignore
        assert isinstance(inst1, MotorModel1)

        MyMotor4 = DeviceBase.bind("my_motor_4", "motor_model_1")
        inst2 = MyMotor4()
        print(inst2.Config)
        assert inst2.Config.switch1 == 4  # type: ignore
        assert isinstance(inst2, MotorModel1)

        assert inst1 is not inst2

    def test_no_reinitialization(self) -> None:
        MyMotor5 = DeviceBase.bind("my_motor_5", "motor_model_3")
        inst = MyMotor5()
        assert isinstance(inst, MotorModel3)
        assert inst.counter == 1

        MyMotor6 = DeviceBase.bind("my_motor_6", "motor_model_3")
        inst = MyMotor6()
        assert isinstance(inst, MotorModel3)
        assert inst.counter == 1

        inst = MotorModel3()
        assert isinstance(inst, MotorModel3)
        assert inst.counter == 1

    def test_support_multi_devices(self) -> None:
        inst = devices.MyMotor7()  # type: ignore
        assert isinstance(inst, Devices)
        assert inst.get_id() == {"a": 2, "b": 1}
        assert inst["a"].get_id() == 2


class TestDeviceSimulator(configured_tester_factory("config_device_simulators")):
    @classmethod
    def setup_class(cls) -> None:
        super().setup_class()
        devices.reload()

    @classmethod
    def teardown_class(cls) -> None:
        super().teardown_class()
        devices.reload()

    def test_simulator(self) -> None:
        cls = devices.MyMotor1  # type: ignore
        assert isinstance(cls, Devices)
        assert not issubclass(cls[None], MotorModel1)
        assert issubclass(cls[None], MotorModel4)

        assert cls.Config.switch1 == 5


class TestDevices(configured_tester_factory("config_devices")):
    @classmethod
    def setup_class(cls) -> None:
        super().setup_class()
        devices.reload()

    @classmethod
    def teardown_class(cls) -> None:
        super().teardown_class()
        devices.reload()

    def test_anonymous(self) -> None:
        MyMotor1 = DeviceBase.bind("my_motor_1", "motor_model_1")
        Motor = Devices(MyMotor1)
        motor = Motor()
        assert isinstance(motor, Devices)
        assert motor.get_id() == 1

    def test_named_single(self) -> None:
        MyMotor1 = DeviceBase.bind("my_motor_1", "motor_model_1")
        Motor = Devices(motor1=MyMotor1)
        motor = Motor()
        assert isinstance(motor, Devices)
        assert motor.get_id() == {"motor1": 1}

    def test_named_multiple(self) -> None:
        MyMotor1 = DeviceBase.bind("my_motor_1", "motor_model_1")
        MyMotor2 = DeviceBase.bind("my_motor_2", "motor_model_2")
        Motor = Devices(motor1=MyMotor1, motor2=MyMotor2)
        motor = Motor()
        assert isinstance(motor, Devices)
        assert motor.get_id() == {"motor1": 1, "motor2": 2}

    def test_anonymous_and_named_cannot_coexist(self) -> None:
        MyMotor1 = DeviceBase.bind("my_motor_1", "motor_model_1")
        MyMotor2 = DeviceBase.bind("my_motor_2", "motor_model_2")
        with pytest.raises(ValueError):
            Devices(MyMotor1, motor2=MyMotor2)

    def test_argument_id_on_named_as_getitem(self) -> None:
        MyMotor1 = DeviceBase.bind("my_motor_1", "motor_model_1")
        MyMotor2 = DeviceBase.bind("my_motor_2", "motor_model_2")
        Motor = Devices(motor1=MyMotor1, motor2=MyMotor2)
        motor = Motor()
        assert motor["motor1.q"].ident() == "q"
        assert motor["motor2.p"].ident() == "p"

    def test_argument_id_on_named_as_method_args(self) -> None:
        MyMotor1 = DeviceBase.bind("my_motor_1", "motor_model_1")
        MyMotor2 = DeviceBase.bind("my_motor_2", "motor_model_2")
        Motor = Devices(motor1=MyMotor1, motor2=MyMotor2)
        motor = Motor()
        assert motor.ident(id="motor1.q") == "q"
        assert motor.ident(id="motor2.p") == "p"

    def test_argument_id_on_anonymous(self) -> None:
        MyMotor1 = DeviceBase.bind("my_motor_1", "motor_model_1")
        Motor = Devices(MyMotor1)
        motor = Motor()
        assert motor["motor1"].ident() == "motor1"

    def test_getitem_id(self) -> None:
        MyMotor1 = DeviceBase.bind("my_motor_1", "motor_model_1")
        MyMotor2 = DeviceBase.bind("my_motor_2", "motor_model_2")
        Motor = Devices(motor1=MyMotor1, motor2=MyMotor2)
        motor = Motor()
        assert motor["motor1"].get_id() == 1
        assert motor["motor2"].get_id() == 2

    def test_partial_initialization(self) -> None:
        MyMotor1 = DeviceBase.bind("my_motor_1", "motor_model_1")
        MyMotor2 = DeviceBase.bind("my_motor_2", "motor_model_2")
        Motor = Devices(motor1=MyMotor1, motor2=MyMotor2)
        motor1 = Motor["motor1"]()
        assert isinstance(motor1, MyMotor1)
