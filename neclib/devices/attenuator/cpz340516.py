import time

from ...core.security import busy
from .attenuator_base import CurrentAttenuator


class CPZ340516(CurrentAttenuator):
    """LOattenuator, which can convert by 8 channels.

    Notes
    -----
    Configuration items for this device:

    channel : Dict[str, int]
        Human-readable channel name. The value should be mapping from human readable
        version (str) to device level identifier (int). You can assign any name to the
        channels. For example, {100GHz = 1}

    range : "DA0_100mA" or "DA0_1mA"
        If DA0_100mA, 1-100mA is possible. Else if DA0_1mA, 1-10mA is possible.
        Default value is DA0_100mA.

    rate : float
        Default value is 0.1.

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
        self.param_buff = {i: 0.0 for i in range(1, 9)}  # All in [mA]
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

    def set_current(self, mA: float, id: str) -> None:
        ch = self.Config.channel[id]
        if ch not in self.param_buff.keys():
            raise ValueError(f"Invaild channel {ch}")
        else:
            self.param_buff[ch] = mA

    def set_outputrange(self, id: int, outputrange: str) -> None:
        self.io.set_outputrange(id, outputrange)

    def apply_current(self) -> None:
        with busy(self, "busy"):
            for i in range(0, 8):
                ch = int(list(self.param_buff.keys())[i])
                current = list(self.param_buff.values())[i]
                self.io.output_current(ch, current)
                time.sleep(0.001)

    def finalize(self) -> None:
        self.io.finalize()
        self.param_buff = {i: 0.0 for i in range(1, 9)}

    def close(self) -> None:
        pass
