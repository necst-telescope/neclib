import ogameasure

from ...core.security import busy
from .ccd_controller_base import CCD_Controller


class M100(CCD_Controller):
    Model = "M100"
    Manufacturer = "Canon"

    Identifier = "host"

    def __init__(self) -> None:
        com = ogameasure.ethernet(self.Config.host, self.Config.port)
        self.ccd = ogameasure.Canon.m100(com)

    def capture(self, savepath: str) -> None:
        with busy(self, "busy"):
            self.ccd.capture(savepath)
            return None

    def finalize(self) -> None:
        self.ccd.com.close()
