from typing import Callable, Union
import astropy.units as u

from ...core.security import busy, sanitize
from .attenuator_base import Attenuator


class CPZ340516(Attenuator):
    # 以下cpz340819より一部コピペ。要変更
    """LOattenuator, which can convert by 8 channels.

    Notes
    -----
    Configuration items for this device:

    rate :

    rsw_id : {0, 1, ..., 16} or {"0", "1", ..., "9", "A", ..., "F"}
        Board identifier. This should be set to the same value as the rotary switch
        "RSW1" mounted on the side of the board. The board is shipped with default RSW1
        setting of 0. This ID would be non-zero, when multiple PCI board of same model
        are mounted on a single FA (Factory Automation) controller.

    channnel_number : int

    See defaults setting file in ``neclib/defaults/config.toml``.

    """

    # Manufacturerとは? Identifierもこれでいいのか要確認
    Manufacturer = ""
    Model = "CPZ340516"

    Identifier = "rsw_id"

    def __init__(self):
        import pyinterface

        self.rate = self.Config.rate
        self.rsw_id = self.Config.rsw_id
        self.param_buff = {i: 0.0 for i in range(1, 17)}

        self.io = pyinterface.open(3405, self.rsw_id)
        # pyinterface/toolsで340816と書き方が違うけど多分？

    def get_loss(self, ch: int) -> u.Quantity:
        with busy(self, "busy"):
            try:
                return self.io.get_outputrange(ch) << u.mA
            except IndexError:
                pass
            raise ValueError(f"Invalid channel: {ch}")

    def set_loss(self, mA: float, id: str, outputrange: str) -> None:
        with busy(self, "busy"):
            ch = self.Config.channel[id]
            self.io.set_outputrange(ch, outputrange)

    def finalize(self) -> None:
        self.io.com.close()
