from typing import Callable, Union

from ...core.security import busy, sanitize
from .da_converter_base import DAConverter


class CPZ340816(DAConverter):
    """d/a converter, which can convert by 32 channels.

    Notes
    -----
    Configuration items for this device:

    rsw_id : {0, 1, ..., 16} or {"0", "1", ..., "9", "A", ..., "F"}
        Board identifier. This should be set to the same value as the rotary switch
        "RSW1" mounted on the side of the board. The board is shipped with default RSW1
        setting of 0. This ID would be non-zero, when multiple PCI board of same model
        are mounted on a single FA (Factory Automation) controller.

    channel : Dict[str, int]
        Human-readable channel name. The value should be mapping from human readable
        version (str) to device level identifier (int). You can assign any name to the
        channels. Defining aliases for unused channels will raise error.

    max_mv : List[int or float]
        Volatage range of this device is supplying. This setting is used for
        check weather the set value is in this range in every "voltage setting”.
        The unit of this value is mV.

    converter : str
        Function to convert setting voltage to any parameter you want.
        Supported ``x`` in function will be substituted by the setting value.
        This would be useful when setting voltage is scaled and/or
        shifted version of physical parameter.

    See defaults setting file in ``neclib/defaults/config.toml``.

    """

    Manufacturer = "Interface"
    Model = "CPZ340816"

    Identifier = "rsw_id"

    def __init__(self):
        import pyinterface

        self.rsw_id = self.Config.rsw_id
        self.param_buff = {i: 0.0 for i in range(1, 17)}  # All in [V]
        self.da = pyinterface.open(3408, self.rsw_id)

    @property
    def converter(self) -> Callable[[Union[int, float]], float]:
        sanitize(self.Config.converter, "x")
        return eval(f"lambda x: {self.Config.converter}")

    def set_voltage(self, mV: float, id: str) -> None:
        ch = self.Config.channel[id]
        if ch not in self.param_buff.keys():
            raise ValueError(f"Invaild channel {ch}")
        if not self.Config.max_mv[0] < mV < self.Config.max_mv[1]:
            raise ValueError(f"Unsafe voltage {mV} mV")
        else:
            self.param_buff[ch] = self.converter(mV)

    def apply_voltage(self) -> None:
        with busy(self, "busy"):
            for i in range(0, 16):
                ch = int(list(self.param_buff.keys())[i])
                voltage = list(self.param_buff.values())[i]

                self.da.output_da(ch, voltage)

    def finalize(self) -> None:
        self.da.finalize()
        self.param_buff = {i: 0.0 for i in range(1, 17)}
