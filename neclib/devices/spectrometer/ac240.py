import socket
import struct

from ... import get_logger
from .spectrometer_base import Spectrometer


class AC240(Spectrometer):
    Model: str = "AC240"
    Identifier = "host"

    def __init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__)

        self.s = socket.socket()
        self.s.connect((self.Config.host, self.Config.port))
        self.msg_fmt = self.Config.msg_fmt
        self.msg_size = struct.calcsize(self.msg_fmt)

    def get_spectra(self):
        received = 0
        d = b''

        while received != self.msg_size:
            d += self.s.recv(self.msg_size - received)
            received = len(d)
            continue

        d = self.msg_unpack(d)

        return d

    def msg_unpack(self, buff):
        ud = struct.unpack(self.msg_fmt, buff)
        dd = {
            'timestamp': ud[0],
            'spectrum': ud[1:16385],
            'total_power': ud[16385+0],
            'integ_time': ud[16385+1],
            'temp_board': int(ud[16385+2]),
            'temp_fpga': ud[16385+3],
            'overflow_fpga': int(ud[16385+4]),
            'overflow_ad': ud[16385+5],
        }
        return dd

    def finalize(self):
        self.s.close()
