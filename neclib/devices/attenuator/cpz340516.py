from ...core.security import busy
from .attenuator_base import CurrentAttenuator


class CPZ340516(CurrentAttenuator):
    """LOattenuator, which can convert by 8 channels.

    Notes
    -----
    Configuration items for this device:

    channel : {{100GHz = 1}}

    range : {"DA0_100mA"} or {"DA0_1mA"}
        If DA0_100mA, 1-100mA is possible. Else if DA0_1mA, 1-10mA is possible.
        Default value is DA0_100mA.

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
        self.range = self.Config.range
        self.channel = self.Config.channel
        self.io = pyinterface.open(3405, self.rsw_id)
        for i in self.channel.values():
            try:
                self.io.set_outputrange(i, self.range)
            except Exception as e:
                if e == "lspci: Unable to load libkmod resources: error -2":
                    pass
                else:
                    raise ValueError(f"Invalid channel: {i}")

    def get_outputrange(self, id: int) -> dict:
        ch = self.Config.channel[id]
        with busy(self, "busy"):
            return self.io.get_outputrange(ch)

    def set_outputrange(self, id: int, outputrange: str):
        self.io.set_outputrange(id, outputrange)

    def output_current(self, id: int, current: float):
        ch = self.Config.channel[id]
        with busy(self, "busy"):
            self.io.output_current(ch, current)

    def finalize(self) -> None:
        self.io.finalize()
