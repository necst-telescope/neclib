__all__ = ["PCI2724"]

import time

from ... import get_logger, utils
from ..motor.motor_base import Motor


class PCI2724(Motor):
    Manufacturer = "Interface"
    Model = "PCI2724"

    Identifier = "rsw_id"

    def __init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__)
        self.rsw_id = self.Config.rsw_id

        self.io = self._initialize_io()

    @utils.skip_on_simulator
    def _initialize_io(self):
        import pyinterface

        io = pyinterface.open(2724, self.rsw_id)
        if io is None:
            raise RuntimeError("Cannot communicate with the PCI board.")

        io.initialize()

        return io

    def memb_open(self) -> None:
        ret = self.io.get_memb_status()
        if ret[1] != 'OPEN':
            buff = [1, 1]
            self.io.output_point(buff, 7)
            while ret[1] != 'OPEN':
                time.sleep(5)
                ret = self.io.get_memb_status()
        buff = [0, 0]
        self.io.output_point(buff, 7)
        return

    def memb_close(self) -> None:
        ret = self.io.get_memb_status()
        if ret[1] != 'CLOSE':
            buff = [0, 1]
            self.io.output_point(buff, 7)
            while ret[1] != 'CLOSE':
                time.sleep(5)
                ret = self.io.get_memb_status()
        buff = [0, 0]
        self.io.output_point(buff, 7)
        return
