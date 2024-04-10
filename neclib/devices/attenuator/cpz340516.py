import astropy.units as u

from ...core.security import busy
from .attenuator_base import Attenuator


class CPZ340516(Attenuator):
    # 以下cpz340819より一部コピペ。要変更
    """LOattenuator, which can convert by 8 channels.

    Notes
    -----
    Configuration items for this device:

    rate : {0.1}

    rsw_id : {0, 1, ..., 7}
        Board identifier. This should be set to the same value as the rotary switch
        "RSW1" mounted on the side of the board. The board is shipped with default RSW1
        setting of 0. This ID would be non-zero, when multiple PCI board of same model
        are mounted on a single FA (Factory Automation) controller.

    See defaults setting file in ``neclib/defaults/config.toml``.

    """

    Manufacturer = "Interface"
    Model = "CPZ340516"

    Identifier = "rsw_id"

    def __init__(self):
        import pyinterface

        self.rsw_id = self.Config.rsw_id
        self.io = pyinterface.open(3405, self.rsw_id)

    def get_loss(self, ch: int, current: float) -> u.Quantity:
        with busy(self, "busy"):
            return self.io.output_current(ch, current) << u.mA

    def set_loss(self, ch: int, outputrange: str) -> None:
        with busy(self, "busy"):
            try:
                self.io.set_outputrange(ch, outputrange)
            except IndexError:
                pass
            raise ValueError(f"Invalid channel: {ch}")

    def finalize(self) -> None:
        self.io.finalize()
