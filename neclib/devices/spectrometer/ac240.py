import queue
import socket
import struct
import time
import traceback
from threading import Event, Thread
from typing import Dict, List, Tuple

from ... import get_logger
from .spectrometer_base import Spectrometer


class AC240(Spectrometer):
    Manufacturer = "Agilent"
    Model: str = "AC240"
    Identifier = "host"

    def __init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__)

        self.s = socket.socket()
        self.s.connect((self.Config.host, self.Config.port))
        self.msg_fmt = self.Config.msg_fmt
        self.msg_size = struct.calcsize(self.msg_fmt)
        self.board_id = self.Config.board_id
        self.data_queue = queue.Queue(maxsize=self.Config.record_quesize)
        self.thread = None
        self.event = None
        self.start()

    def start(self) -> None:
        if (self.thread is not None) or (self.event is not None):
            self.stop()
        self.thread = Thread(target=self._read_data, daemon=True)
        self.event = Event()
        self.thread.start()

    def receive(self):
        received = 0
        d = b""

        while received != self.msg_size:
            d += self.s.recv(self.msg_size - received)
            received = len(d)
            continue

        d = self.msg_unpack(d)

        return d

    def msg_unpack(self, buff):
        ud = struct.unpack(self.msg_fmt, buff)
        dd = {
            "timestamp": ud[0],
            "spectrum": ud[1:16385],
            "total_power": ud[16385 + 0],
            "integ_time": ud[16385 + 1],
            "temp_board": int(ud[16385 + 2]),
            "temp_fpga": ud[16385 + 3],
            "overflow_fpga": int(ud[16385 + 4]),
            "overflow_ad": ud[16385 + 5],
        }
        return dd

    def _read_data(self) -> None:
        while (self.event is not None) and (not self.event.is_set()):
            if self.data_queue.full():
                if self.warn:
                    self.logger.warning(
                        "Dropping the data due to low readout frequency."
                    )
                    self.warn = False
                self.data_queue.get()

            try:
                data = self.receive()
                self.data_queue.put((time.time(), {self.board_id: data["spectrum"]}))

            except struct.error:
                exc = traceback.format_exc()
                self.logger.warning(exc[slice(0, min(len(exc), 100))])

    def get_spectra(self) -> Tuple[float, Dict[int, List[float]]]:
        self.warn = True
        return self.data_queue.get()

    def stop(self) -> None:
        if self.event is not None:
            self.event.set()
        if self.thread is not None:
            self.thread.join()
        self.event = self.thread = None

    def finalize(self):
        self.stop()
        self.s.close()

    def change_spec_ch(self, chan):
        self.logger.warning("AC240 have not implemented binning mode yet.")
        pass
