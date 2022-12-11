import os
import queue
import struct
import sys
import time
import traceback
from contextlib import contextmanager
from threading import Event, Thread
from typing import Dict, Generator, List, Tuple

import xfftspy

from ... import get_logger
from .spectrometer_base import Spectrometer


class XFFTS(Spectrometer):

    Manufacturer: str = "Radiometer Physics GmbH"
    Model: str = "XFFTS"

    Identifier = "host"

    def __init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__)

        self.host = self.Config.host
        self.cmd_port = self.Config.cmd_port
        self.data_port = self.Config.data_port
        self.synctime_us = self.Config.synctime_us
        self.bw_mhz = {int(k): v for k, v in self.Config.bw_mhz.items()}
        self.data_input, self.setting_output = self.initialize()

        self.data_queue = queue.Queue(maxsize=2)
        self.thread = None
        self.event = None
        self.start()

        self.warn = False

    def start(self) -> None:
        if (self.thread is not None) or (self.event is not None):
            self.stop()
        self.thread = Thread(target=self._read_data, daemon=True)
        self.event = Event()
        self.thread.start()

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
                data = self.data_input.receive_once()
                self.data_queue.put((time.time(), data["data"]))
            except struct.error:
                exc = traceback.format_exc()
                self.logger.warning(exc[slice(0, min(len(exc), 100))])

    def stop(self) -> None:
        if self.event is not None:
            self.event.set()
        if self.thread is not None:
            self.thread.join()
        self.event = self.thread = None
        self.warn = False

    def initialize(self) -> Tuple[xfftspy.data_consumer, xfftspy.udp_client]:
        """Get configured data input and setting output."""
        setting_output = xfftspy.udp_client(self.host, self.cmd_port, print=False)
        setting_output.stop()
        setting_output.set_synctime(self.synctime_us)  # synctime in us
        _sections = [int(i in self.bw_mhz) for i in range(1, max(self.bw_mhz) + 1)]
        setting_output.set_usedsections(_sections)
        for board_id, bw_mhz in self.bw_mhz.items():
            setting_output.set_board_bandwidth(board_id, bw_mhz)
        setting_output.configure()  # Apply settings
        setting_output.caladc()  # Calibrate ADCs
        setting_output.start()

        data_input = xfftspy.data_consumer(self.host, self.data_port)
        data_input.clear_buffer()
        return data_input, setting_output

    def get_spectra(self) -> Tuple[float, Dict[int, List[float]]]:
        self.warn = True
        return self.data_queue.get()

    def finalize(self) -> None:
        self.setting_output.stop()
        self.stop()


@contextmanager
def mute_stderr() -> Generator[None, None, None]:
    stderr = sys.stderr
    sys.stderr = open(os.devnull, "w")
    try:
        yield
    except Exception:
        pass
    finally:
        sys.stderr = stderr
