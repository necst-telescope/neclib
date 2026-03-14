import ogameasure

from ...core.security import busy
from .ccd_controller_base import CCDController


class D7100(CCDController):
    Model = "D7100"
    Manufacturer = "Nikon"
    Identifier = "host"

    def __init__(self) -> None:
        self.ccd = ogameasure.Nikon.d7100()

    def capture(self, savepath: str) -> None:
        with busy(self, "busy"):
            self.ccd.capture(savepath)
            return None

    def finalize(self) -> None:
        return None

    def close(self) -> None:
        self.finalize()
