import logging
import time
from typing import Dict, Optional, Union

from .. import environ


class ColorizeLevelNameFormatter(logging.Formatter):
    """Colorize severity level name.

    See `logging docs <https://docs.python.org/3/library/logging.html#handler-objects>`_
    for the usage.

    """

    ColorPrefix: Dict[int, str] = {
        0: "\x1b[0m",  # NOTSET, default (Black or White)
        10: "\x1b[35m",  # DEBUG, Magenta
        20: "\x1b[32m",  # INFO, Green
        30: "\x1b[33m",  # WARNING, Yellow
        40: "\x1b[31m",  # ERROR, Red
        50: "\x1b[41;97m",  # CRITICAL, White on Red
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format a record to text."""
        levelno = int(min(max(0, record.levelno // 10 * 10), 50))
        original_levelname = record.levelname
        record.levelname = self.ColorPrefix[levelno] + original_levelname + "\x1b[0m"
        return super().format(record)


class Throttle(logging.Filter):
    """Reduce logging frequency of identical messages.

    Parameters
    ----------
    duration_sec
        Duration in seconds. If the same message is logged within this duration,
        attached handlers discard it.

    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, duration_sec: Union[int, float]):
        super().__init__(name=self.__class__.__name__)
        self._duration_sec = duration_sec
        if not hasattr(self, "_last_log_time"):
            # Calling singleton class will return the same instance, but the __init__
            # method will be called again. That will empty the time keeper, so
            # initialize this dictionary only when it is not defined.
            self._last_log_time: Dict[str, float] = {}

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter function to be attached to logger."""
        now = time.time()
        for k in list(self._last_log_time.keys()):
            # Comparing `now` with `record.created` is not accurate, but this is to
            # reduce memory consumption, i.e., otherwise self._last_log_time would be
            # filled by infrequent logs.
            if now - self._last_log_time[k] > self._duration_sec:
                self._last_log_time.pop(k, None)

        key = (record.levelno, record.msg)
        if key in self._last_log_time:
            return False
        self._last_log_time[key] = record.created
        return True


def get_logger(
    name: Optional[str] = None,
    min_level: int = None,
    throttle_duration_sec: Union[int, float] = 1.0,
) -> logging.Logger:
    """Get logger instance which prints operation logs to console.

    Parameters
    ----------
    name
        Name of the logger. Calling this function with same ``name`` returns the same
        logger instance.
    min_level
        Lower bound of severity level to be displayed on terminal. To suppress less
        severe messages, set higher value. No matter this value, the log file contains
        all messages severer than ``logging.INFO`` (level=20).
    throttle_duration_sec
        Duration in seconds to throttle messages. If the same message is logged within
        this duration, the message is not displayed on terminal.

    Examples
    --------
    >>> logger = neclib.interfaces.getLogger("OTF_observation", "path/to/log.txt")
    >>> logger.debug("Inform something only needed on diagnosing some problem.")
    >>> logger.info("Inform something EXPECTED has happened.")
    >>> logger.warning("Inform something user should care has happened.")
    >>> logger.error(f"Notify some {functionality} cannot be completed due to error.")
    >>> logger.critical(
    ...     "Notify the %s cannot continue operation due to %s", "program", "some error"
    ... )
    >>> logger.obslog("Observation finished", indent_level=1)

    """
    logger_name = "neclib" if name is None else f"neclib.{name.strip('neclib.')}"
    logger = logging.getLogger("necst." + logger_name)
    [logger.removeHandler(f) for f in logger.filters if isinstance(f, Throttle)]
    logger.addFilter(Throttle(throttle_duration_sec))

    min_level = environ.log_level.get() if min_level is None else min_level

    fmt = "%(asctime)-s: [%(levelname)-s: %(filename)s#L%(lineno)s] %(message)s"
    color_log_format = ColorizeLevelNameFormatter(fmt)

    ch = logging.StreamHandler()
    ch.setLevel(min_level)
    ch.setFormatter(color_log_format)

    rootLogger = logging.getLogger()
    chs = [_ch for _ch in rootLogger.handlers if isinstance(_ch, logging.StreamHandler)]
    [rootLogger.handlers.remove(_ch) for _ch in chs]
    rootLogger.addHandler(ch)

    return logger
