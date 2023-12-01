import ogameasure

from ...core.security import busy
from .ccd_controller_base import CCDController


class M100(CCDController):

    """ccd camera, which can capture stars when optical pointing.

    Notes
    -----
    You need to install ``libgphoto2`` library in advance.

    Configuration items for this device:

    pic_captured_path : str
        Save directory path of pictures captured by ccd camera.
        This path must be absolute path.
        e.g. ``/home/pi/data/optical_pointing``

    See defaults setting file in ``neclib/defaults/config.toml``.

    """

    Model = "M100"
    Manufacturer = "Canon"

    Identifier = "host"

    def __init__(self) -> None:
        self.ccd = ogameasure.Canon.m100()

    def capture(self, savepath: str) -> None:
        with busy(self, "busy"):
            self.ccd.capture(savepath)
            return None

    def finalize(self) -> None:
        self.ccd.com.close()
