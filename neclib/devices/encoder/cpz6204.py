__all__ = ["CPZ6204"]

from ... import utils, get_logger
from .encoder_base import Encoder
from astropy import units as u


class CPZ6204(Encoder):
    # """Encoder readout.

    # Notes
    # -----
    # Configuration items for this device:
    # rsw_id : {0, 1, ..., 16} or {"0", "1", ..., "9", "A", ..., "F"}
    #     Board identifier. This should be set to the same value as the rotary switch
    #     "RSW1" mounted on the side of the board. The board is shipped with default
    #     RSW1 setting of 0. This ID would be non-zero, when multiple PCI board of same
    #     model are mounted on a single FA (Factory Automation) controller.
    # See defaults setting file in neclib/defaults/config.toml.
    # """

    Manufacturer = "Interface"
    Model = "CPZ6204"

    Identifier = "rsw_id"

    def __init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__)
        self.rsw_id = self.Config.rsw_id

        self.enc_Az = 0
        self.enc_El = 45 * 3600
        self.resolution = 360 * 3600 / (23600 * 400)

        self.io = self._initialize()

    @utils.skip_on_simulator
    def _initialize(self):
        import pyinterface

        io = pyinterface.open(6204, self.rsw_id)
        if io is None:
            raise RuntimeError("Cannot communicate with the CPZ board.")
        mode = io.get_mode()
        if mode["mode"] == "":
            io.set_mode(mode="MD0 SEL1", direction=1, equal=0, latch=0, ch=1)
            io.set_mode(mode="MD0 SEL1", direction=1, equal=0, latch=0, ch=2)
            self.board_setting(io)
        io.initialize()
        io.reset(ch=1)
        io.set_mode("MD0", 0, 1, 0, ch=1)

        return io

    def get_dome_reading(self):
        self.dome_encoffset = self.Config.dome_encoffset
        self.dome_enc1loop = self.Config.dome_enc1loop
        self.dome_enc2arcsec = 3600.0 * 360 / self.dome_enc1loop
        self.dome_enc_tel_offset = self.Config.dome_enc_tel_offset * 360
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

    def get_reading(self):
        cntAz = int(self.io.get_counter(unsigned=False, ch=1))
        cntEl = int(self.io.get_counter(unsigned=False, ch=2))
        """unsigned
        if cntAz < 360*3600./self.resolution:
            #encAz = (324*cntAz+295)/590
            encAz = cntAz*self.resolution
        else:
            encAz = -(2**32-cntAz)*self.resolution
            pass
        """
        encAz = cntAz * self.resolution
        Az = encAz * u.arcsec
        """ unsigned
        if cntEl < 360*3600./self.resolution:
            #encEl = (324*cntEl+295)/590
            encEl = cntEl*self.resolution
        else:
            encEl = -(2**32-cntEl)*self.resolution
            pass
        """
        encEl = cntEl * self.resolution
        El = encEl + 45 * 3600 * u.arcsec
        AzEl = {"Az": Az, "El": El}

        return AzEl  # , _utc]

    def finalize(self) -> None:
        pass

    def board_setting(self, io, z_mode=""):
        self.logger.info("Initialize start")
        io.set_z_mode(clear_condition=z_mode, latch_condition="", z_polarity=0, ch=1)
        io.set_z_mode(clear_condition=z_mode, latch_condition="", z_polarity=0, ch=2)
        print("origin setting mode : ", z_mode)
        self.logger.info("initialize end")
        return
