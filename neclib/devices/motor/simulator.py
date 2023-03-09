import astropy.units as u

from .motor_base import Motor


class MotorSimulator(Motor):
    Manufacturer: str = ""
    Model: str = ""
    Identifier = ""
    is_simulator = True

    def __init__(self) -> None:
        self.motion = ...

    def set_step(self, step: int, axis: str) -> None:
        """Drive to (maybe device-specific) absolute position."""
        raise NotImplementedError

    def set_speed(self, speed: float, axis: str) -> None:
        raise NotImplementedError

    def get_step(self, axis: str) -> int:
        """Maybe device-specific absolute position."""
        raise NotImplementedError

    def get_speed(self, axis: str) -> u.Quantity:
        raise NotImplementedError

    def finalize(self) -> None:
        pass
