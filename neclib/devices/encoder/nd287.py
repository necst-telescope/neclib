__all__ = ["ND287"]

import astropy.units as u
import ogameasure

from .encoder_base import Encoder


class ND287(Encoder):
    """Encoder readout.

    Parameters
    ----------
    port
        Device path in UNIX file system, like ``"/dev/ttyUSB1"``.

    """

    Manufacturer = "HEIDENHAIN"
    Model = "ND287"

    def __init__(self, port: str) -> None:
        self.driver = ogameasure.HEIDENHAIN.ND287(port)

    def get_reading(self) -> u.Quantity:
        raw = self.driver.output_position_display_value()
        return float(raw.strip(b"\x02\x00\r\n").decode())
