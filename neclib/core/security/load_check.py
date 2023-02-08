import time
from typing import Dict, Optional

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

    def cpu_usage(self) -> Quantity:
        """Mean CPU usage since last call.

        Since this method averages the usage from last call, the initial call returns
        meaningless 0.

        """
        usage = psutil.cpu_percent(interval=None, percpu=True)
        if usage is None:
            return [0] * self.cpu_count * u.percent
        return usage * u.percent

    def memory_available(self) -> Quantity:
        """Available memory."""
        return psutil.virtual_memory().available * u.byte

    def disk_usage(self) -> Quantity:
        """Disk (storage) usage."""
        return psutil.disk_usage("/").percent * u.percent

    def network_amount(self) -> Dict[str, Quantity]:
        """Network communication amount.

        Mean data rate of network communications. The value is averaged from last call.
        The initial call returns meaningless 0.

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
