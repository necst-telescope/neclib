from typing import Literal

import astropy.units as u
import ogameasure

from .attenuator_base import Attenuator


class RHIO10(Attenuator):

    Manufacturer: str = "SENA"
    Model: str = "RHIO10"

    Identifier = "host"

    def __init__(self) -> None:
        com = ogameasure.ethernet(self.Config.host, self.Config.port)
        self.io = ogameasure.SENA.adios(com)

    def get_level(self, ch: Literal[1, 2]) -> u.Quantity:
        if ch == 1:
            return self.io.get_att1() << u.dB
        elif ch == 2:
            return self.io.get_att2() << u.dB
        raise ValueError(f"Invalid channel number: {ch}")

    def set_level(self, level_dB: int, ch: Literal[1, 2]) -> None:
        self.io._set_att(ch, int(level_dB))

    def finalize(self) -> None:
        self.io.com.close()
