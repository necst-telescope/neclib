import time
from typing import Dict, Optional, Tuple

import astropy.units as u
import psutil
from astropy.units import Quantity


class LoadChecker:
    cpu_count = psutil.cpu_count()
    """Number of logical processors.

    Number of threads that can be handled simultaneously. Normally this is the same as
    the number of CPU cores. If simultaneous multi-threading is enabled (e.g., Intel's
    Hyper-Threading technology), this value would be larger than the number of CPU
    cores.

    """

    def __init__(self):
        self._last_netcount: Optional[Dict[str, float]] = None

        # Ensure that the first call of methods returns meaningful values.
        self.cpu_usage()
        self.network_amount()

    def cpu_usage(self) -> Quantity:
        """Mean CPU usage since last call.

        This method averages the usage from last call or class initialization.

        """
        usage = psutil.cpu_percent(interval=None, percpu=True)
        return usage * u.percent

    def loadavg(self) -> Tuple[float, float, float]:
        """Load average per processor.

        Returns
        -------
        Number of processes using or waiting to use the processor, averaged over all
        logical processors. The load is averaged over time duration of 1min, 5min, and
        15min.

        """
        return tuple(load / self.cpu_count for load in psutil.getloadavg())

    def memory_available(self) -> Quantity:
        """Available memory."""
        return psutil.virtual_memory().available * u.byte

    def disk_usage(self) -> Quantity:
        """Disk (storage) usage."""
        return psutil.disk_usage("/").percent * u.percent

    def network_amount(self) -> Dict[str, Quantity]:
        """Network communication amount.

        This method averages the data rate from last call or class initialization.

        """
        netcount = psutil.net_io_counters()
        current_netcount: Dict[str, float] = {
            "sent": netcount.bytes_sent,
            "recv": netcount.bytes_recv,
            "time": time.monotonic(),
        }
        if self._last_netcount is None:
            self._last_netcount = current_netcount
            return {"sent": 0 * u.byte / u.s, "recv": 0 * u.byte / u.s}

        dt = current_netcount["time"] - self._last_netcount["time"]
        dsent = netcount.bytes_sent - self._last_netcount["sent"]
        drecv = netcount.bytes_recv - self._last_netcount["recv"]
        self._last_netcount = current_netcount
        return {"sent": dsent / dt * u.byte / u.s, "recv": drecv / dt * u.byte / u.s}
