import astropy.units as u

from ...core.math import Random
from .ad_converter_base import ADConverter


class ADConverterSimulator(ADConverter):
    Manufacturer: str = ""
    Model: str = ""
    Identifier = ""
    is_simulator = True

    def __init__(self) -> None:
        self._rand = Random().walk(-16, 0.1, -1)

    def get_all(self, target: str) -> dict:
        raise NotImplementedError

    def get_from_id(self, id: str) -> u.Quantity:
        raise NotImplementedError

    def finalize(self) -> None:
        pass

    def close(self) -> None:
        pass
