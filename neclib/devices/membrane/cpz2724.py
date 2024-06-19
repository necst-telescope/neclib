__all__ = ["CPZ2724"]

import time

from ... import get_logger, utils
from .membrane_base import Membrane


class CPZ2724(Membrane):
    Manufacturer = "Interface"
    Model = "CPZ2724"

    Identifier = "rsw_id"

    def __init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__)
        self.rsw_id = self.Config.rsw_id

        self.io = self._initialize_io()

    @utils.skip_on_simulator
    def _initialize_io(self):
        import pyinterface

        self.io = pyinterface.open(2724, self.rsw_id)
        if self.io is None:
            raise RuntimeError("Cannot communicate with the CPZ board.")

        self.io.initialize()

        return self.io

    def memb_open(self) -> None:
        ret = self.io.get_latch_status()
        if ret[1] != "OPEN":
            buff = [1, 1]
            self.io.output_point(buff, 7)
            while ret[1] != "OPEN":
                time.sleep(5)
                ret = self.io.get_latch_status()
        buff = [0, 0]
        self.io.output_point(buff, 7)
        return

    def memb_close(self) -> None:
        ret = self.io.get_latch_status()
        if ret[1] != "CLOSE":
            buff = [0, 1]
            self.io.output_point(buff, 7)
            while ret[1] != "CLOSE":
                time.sleep(5)
                ret = self.io.get_latch_status()
        buff = [0, 0]
        self.io.output_point(buff, 7)
        return
