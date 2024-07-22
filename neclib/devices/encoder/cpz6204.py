__all__ = ["CPZ6204"]

import astropy.units as u

from ... import utils
from ...core.security import busy
from .encoder_base import Encoder


class CPZ6204(Encoder):
    """Encoder readout.

    Notes
    -----

    Configuration items for this device:

    port : int
        USB port of using devices.

    """

    Manufacturer = "Interface"
    Model = "CPZ6204"

    Identifier = "rsw_id"

    def __init__(self) -> None:
        self.rsw_id = self.Config.rsw_id
        self.dome_encoffset = self.Config.dome_encoffset
        self.dome_enc1loop = self.Config.dome_enc1loop
        self.dome_enc2arcsec = 3600.0 * 360 / self.dome_enc1loop

        self.io = self._initialize()

    @utils.skip_on_simulator
    def _initialize(self):
        import pyinterface

        io = pyinterface.open(6204, self.rsw_id)
        if self.io is None:
            raise RuntimeError("Cannot communicate with the CPZ board.")
        io.initialize()
        io.reset(ch=1)
        io.set_mode("MD0", 0, 1, 0, ch=1)

        return io

    def dome_encoder_acq(self):
        # counter = self.dio.get_position()
        counter = self.io.get_counter(ch=1)
        # print('self,dio.get_counter : ', counter.to_int())
        counter = int(counter)  # .to_int()
        dome_enc_arcsec = -int(
            ((counter - self.dome_encoffset) * self.dome_enc2arcsec)
            - self.dome_enc_tel_offset
        )
        while dome_enc_arcsec > 1800.0 * 360:
            dome_enc_arcsec -= 3600.0 * 360
        while dome_enc_arcsec <= -1800.0 * 360:
            dome_enc_arcsec += 3600.0 * 360
        self.dome_position = dome_enc_arcsec
        return self.dome_position

    def finalize(self) -> None:
        pass
