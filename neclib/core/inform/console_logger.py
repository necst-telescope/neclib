import logging
import os
from typing import Dict, Optional


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


def get_logger(
    name: Optional[str] = None,
    min_level: int = None,
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
        all messages severer than ``logging.DEBUG`` (level=10).

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

    min_level = (
        int(os.environ.get("NECST_LOG_LEVEL", logging.INFO))
        if min_level is None
        else min_level
    )

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
