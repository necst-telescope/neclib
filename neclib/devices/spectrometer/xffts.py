import inspect
import queue
import socket
import time
import traceback
from threading import Event, Lock, Thread
from typing import Any, Dict, List, Tuple

import xfftspy

from ... import get_logger
from .spectrometer_base import Spectrometer


class XFFTS(Spectrometer):
    """Spectrometer, which can do FFT in 8 IF.

    Notes
    -----

    Configuration items for this device:

    host : str
        IP address for ethernet communicator.
        If you operate this device in local network, you should be set
        this parameter to “localhost”.

    data_port : int
        Ethernet port  of using devices. This port is used for data
        transmmition. The default value of this device is 25144.

    cmd_port : str
        Ethernet port  of using devices. This port is used for command
        operation. The default value of this device is 16210.

    synctime_us : int
        Sync time of data transmmition in unit us. The minimum value of
        this device is 100000.

    bw_MHz : Dict[int]
        Band width of each XFFTS boads in MHz unit.
        You must define this parameter to all boad which you use.
        For Example: You use 4 boads and set band width to 2000 MHz,
        ``{ 1 = 2000, 2 = 2000, 3 = 2000, 4 = 2000 }``
        The maximum value of band width is 2500 MHz.

    max_ch : int
        Max spectral channel of spectrometer. This number should be
        power of 2.
        The maximum number of this device is 32768.

    See defaults setting file in ``neclib/defaults/config.toml``.

    """

    Manufacturer: str = "Radiometer Physics GmbH"
    Model: str = "XFFTS"

    Identifier = "host"

    def __init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__)

        self.host = self.Config.host
        self.cmd_port = self.Config.cmd_port
        self.data_port = self.Config.data_port
        self.synctime_us = self.Config.synctime_us
        self.bw_mhz = {int(k): v for k, v in self.Config.bw_MHz.items()}

        # A blocking TCP recv must not prevent NECST abort/finalize from returning.
        # Keep the default comfortably longer than the XFFTS sync interval, while
        # still finite so that cable/server failures become visible.
        self.data_timeout_sec = float(
            getattr(
                self.Config,
                "data_timeout_sec",
                max(5.0, 5.0 * float(self.synctime_us) / 1_000_000.0),
            )
        )
        self.reconnect_interval_sec = float(
            getattr(self.Config, "reconnect_interval_sec", 2.0)
        )
        self.join_timeout_sec = float(getattr(self.Config, "join_timeout_sec", 3.0))

        self.data_input = None
        self.setting_output = None
        self._data_lock = Lock()
        self._last_reconnect_attempt = 0.0
        self.reconnect_count = 0
        self.last_exception = ""
        self.last_exception_time = 0.0
        self.last_receive_time = 0.0
        self.last_receive_header: Dict[str, Any] = {}

        self.data_input, self.setting_output = self.initialize()

        self.data_queue = queue.Queue(maxsize=self.Config.record_quesize)
        self.thread = None
        self.event = None
        self.warn = False
        self.start()

    def _require_fast_xfftspy(self) -> None:
        """Fail early when an old tuple-only xfftspy is installed.

        The old ``xfftspy.data_consumer`` creates a Python float tuple for every
        channel of every board.  At 32768 channels this is too slow and can make
        the XFFTS FitsWriter side report ``Sending dump ... failed``.  NECST now
        requires the zero-copy ``return_numpy=True`` data path.
        """

        try:
            sig = inspect.signature(xfftspy.data_consumer)
        except Exception as exc:
            raise RuntimeError(
                "Cannot inspect xfftspy.data_consumer; please reinstall the "
                "updated xfftspy package with return_numpy support."
            ) from exc

        if "return_numpy" not in sig.parameters:
            path = getattr(xfftspy, "__file__", "unknown")
            raise RuntimeError(
                "Installed xfftspy is too old for NECST XFFTS readout. "
                "It does not support data_consumer(..., return_numpy=True), "
                "so it falls back to slow Python tuple spectra and can cause "
                "XFFTS 'Sending dump failed' errors. "
                f"Installed xfftspy path: {path}. "
                "Install the updated xfftspy package before observing."
            )

    def _configure_data_socket(self, data_input) -> None:
        sock = getattr(data_input, "sock", None)
        if sock is None:
            return
        try:
            sock.settimeout(self.data_timeout_sec)
        except Exception as exc:
            self.logger.warning(f"Failed to set XFFTS socket timeout: {exc!r}")

    def _open_data_consumer(self):
        self._require_fast_xfftspy()
        data_input = xfftspy.data_consumer(
            self.host,
            self.data_port,
            return_numpy=True,
        )
        self._configure_data_socket(data_input)
        return data_input

    def _close_data_consumer(self) -> None:
        data_input = self.data_input
        if data_input is None:
            return
        try:
            data_input.close()
        except Exception:
            sock = getattr(data_input, "sock", None)
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass

    def _clear_data_buffer(self, context: str) -> None:
        data_input = self.data_input
        if data_input is None:
            return
        try:
            data_input.clear_buffer()
        except (socket.timeout, TimeoutError) as exc:
            # A timeout here is not fatal: it often means START has not produced
            # enough packets yet.  The read thread will reconnect/report if the
            # stream remains broken.
            self._note_exception(f"XFFTS clear_buffer timeout during {context}: {exc!r}")
        except Exception as exc:
            self._note_exception(f"XFFTS clear_buffer failed during {context}: {exc!r}")

    def _note_exception(self, message: str) -> None:
        self.last_exception = str(message)
        self.last_exception_time = time.time()

    def _reconnect_data_consumer(self, reason: str) -> bool:
        if (self.event is not None) and self.event.is_set():
            return False
        now = time.time()
        if now - self._last_reconnect_attempt < self.reconnect_interval_sec:
            return False
        self._last_reconnect_attempt = now

        with self._data_lock:
            if (self.event is not None) and self.event.is_set():
                return False
            self.logger.warning(f"Reconnecting XFFTS data stream after: {reason}")
            try:
                self._close_data_consumer()
                self.data_input = self._open_data_consumer()
                self.reconnect_count += 1
                self._clear_data_buffer("reconnect")
                return True
            except Exception as exc:
                tb = traceback.format_exc()
                self._note_exception(
                    f"XFFTS data stream reconnect failed: {exc!r}\n{tb[:500]}"
                )
                return False

    def start(self) -> None:
        if (self.thread is not None) or (self.event is not None):
            self.stop(close_input=False)
        self.event = Event()
        self.thread = Thread(target=self._read_data, daemon=True)
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
                with self._data_lock:
                    if self.data_input is None:
                        raise RuntimeError("XFFTS data_consumer is not connected")
                    data = self.data_input.receive_once()
                header = data.get("header", {})
                time_spectrometer = header["timestamp"].decode()
                try:
                    received_time = float(header.get("received_time", time.time()))
                except Exception:
                    received_time = time.time()
                self.last_receive_time = float(received_time)
                self.last_receive_header = dict(header)
                self.data_queue.put((received_time, time_spectrometer, data["data"]))
            except Exception as exc:
                if (self.event is not None) and self.event.is_set():
                    break
                tb = traceback.format_exc()
                self._note_exception(f"{exc!r}\n{tb[:500]}")
                self.logger.warning(f"XFFTS data receive failed: {exc!r}")
                if not self._reconnect_data_consumer(str(exc)):
                    time.sleep(min(1.0, self.reconnect_interval_sec))

    def stop(self, *, close_input: bool = True) -> None:
        if self.event is not None:
            self.event.set()
        if close_input:
            # Closing the socket unblocks recv(), allowing abort/finalize to return.
            self._close_data_consumer()
        if self.thread is not None:
            self.thread.join(timeout=self.join_timeout_sec)
            if self.thread.is_alive():
                self.logger.warning(
                    "XFFTS reader thread did not stop within "
                    f"{self.join_timeout_sec:.1f} s"
                )
        self.event = self.thread = None
        self.warn = False

    def initialize(self) -> Tuple[xfftspy.data_consumer, xfftspy.udp_client]:
        """Get configured data input and setting output."""
        # Fail before starting/reconfiguring hardware if the Python receiver is too old.
        self._require_fast_xfftspy()

        setting_output = xfftspy.udp_client(self.host, self.cmd_port, print=False)
        setting_output.stop()
        setting_output.set_synctime(self.synctime_us)  # synctime in us
        _sections = [int(i in self.bw_mhz) for i in range(1, max(self.bw_mhz) + 1)]
        setting_output.set_usedsections(_sections)
        for board_id, bw_mhz in self.bw_mhz.items():
            setting_output.set_board_bandwidth(board_id, bw_mhz)
        setting_output.configure()  # Apply settings
        setting_output.caladc()  # Calibrate ADCs

        # Connect the TCP data consumer before START so the first dumps have a
        # receiver.  This avoids the common START -> dump 1 failed race.
        data_input = self._open_data_consumer()
        self.data_input = data_input
        setting_output.start()
        self._clear_data_buffer("initialize")
        return data_input, setting_output

    def get_spectra(self) -> Tuple[float, Dict[int, List[float]]]:
        self.warn = True
        return self.data_queue.get()

    def change_spec_ch(self, chan):
        # Reconfiguration changes the packet size.  Stop the read thread and
        # reopen the TCP stream so the next header/data pair is synchronized.
        self.stop(close_input=True)
        self.setting_output.stop()
        for board in self.bw_mhz.keys():
            self.logger.info(
                f"Record channel number changed; {chan} ch data will be saved"
            )
            self.setting_output.set_board_numspecchan(board, chan)
        self.setting_output.configure()
        self.data_input = self._open_data_consumer()
        self.setting_output.start()
        self._clear_data_buffer("change_spec_ch")
        self.start()

    def finalize(self) -> None:
        try:
            self.setting_output.stop()
        finally:
            self.stop(close_input=True)
