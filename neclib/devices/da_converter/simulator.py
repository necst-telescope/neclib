from .da_converter_base import DAConverter


class DAConverterSimulator(DAConverter):
    Manufacturer: str = ""
    Model: str = ""
    Identifier = ""
    is_simulator = True

    def __init__(self) -> None:
        ...

    def set_voltage(self, mV: float, id: str) -> None:
        raise NotImplementedError

    def apply_voltage(self) -> None:
        raise NotImplementedError

    def finalize(self) -> None:
        pass
