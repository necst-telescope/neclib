from ...core.security import busy
from .attenuator_base import CurrentAttenuator


class CPZ340516(CurrentAttenuator):
    # 以下cpz340819より一部コピペ。要変更
    """LOattenuator, which can convert by 8 channels.

    Notes
    -----
    Configuration items for this device:

    rate : {0.1}

    rsw_id : {0, 1, ..., 16} or {"0", "1", ..., "9", "A", ..., "F"}
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

    def get_outputrange(self, ch: int, outputrange: str) -> dict:
        with busy(self, "busy"):
            return self.io.get_outputrange(ch, outputrange)

    def set_outputrange(self, ch: int, outputrange: str) -> None:
        with busy(self, "busy"):
            try:
                self.io.set_outputrange(ch, outputrange)
            except IndexError:
                pass
            raise ValueError(f"Invalid channel: {ch}")

    def output_current(self, ch: int, current: float):
        with busy(self, "busy"):
            self.io.output_current(ch, current)

    def finalize(self) -> None:
        self.io.finalize()
