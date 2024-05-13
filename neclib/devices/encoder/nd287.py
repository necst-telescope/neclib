__all__ = ["ND287"]

import astropy.units as u
import ogameasure

from ... import utils
from ...core.security import busy
from .encoder_base import Encoder


class ND287(Encoder):
    """Encoder readout.

    Notes
    -----

    Configuration items for this device:

    port : int
        USB port of using devices.

    """

    Manufacturer = "HEIDENHAIN"
    Model = "ND287"

    Identifier = "port"

    @utils.skip_on_simulator
    def __init__(self) -> None:
        self.io = ogameasure.HEIDENHAIN.ND287(self.Config.port)

    def get_reading(self) -> u.Quantity:
        with busy(self, "busy"):
            raw = self.io.output_position_display_value()
        return float(raw.strip(b"\x02\x00\r\n").decode()) << u.deg  # type: ignore

    def finalize(self) -> None:
        try:
            self.io._enc.close()
        except AttributeError:
            pass
