__all__ = ["getLogger", "ColorizeLevelNameFormatter"]

import logging
from typing import Dict

from .. import utils
from ..typing import PathLike


def getLogger(
    name: str, file_path: PathLike, min_level: int = logging.DEBUG
) -> logging.Logger:
    """Get logger instance which prints operation logs to console and dumps to file.

    Parameters
    ----------
    name
        Name of the logger. Calling this function with same ``name`` returns the same
        logger instance.
    file_path
        Path to file into which logs are dumped.
    min_level
        Lower bound of severity level to be displayed on terminal. To suppress less
        severe messages, set higher value. No matter this value, the log file contains
        all messages severer than DEBUG (lv=10).

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

    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    def add_handler_and_remove_first_duplicate(new: logging.Handler) -> None:
        logger.addHandler(new)
        type_ = type(new)
        match = [isinstance(handler, type_) for handler in logger.handlers]
        idx = [i for i in range(len(match)) if match[i] is True]
        if len(idx) > 1:
            logger.handlers.pop(idx[0])

    fmt = "%(asctime)-s: [%(levelname)-8s: %(filename)s:%(lineno)s] %(message)s"
    color_log_format = ColorizeLevelNameFormatter(fmt)
    text_log_format = logging.Formatter(fmt)

    fh = logging.FileHandler(file_path)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(text_log_format)
    add_handler_and_remove_first_duplicate(fh)

    ch = logging.StreamHandler()
    ch.setLevel(min_level)
    ch.setFormatter(color_log_format)
    add_handler_and_remove_first_duplicate(ch)

    return logger


class ColorizeLevelNameFormatter(logging.Formatter):
    """Colorize severity level name.

    See `logging docs <https://docs.python.org/3/library/logging.html#handler-objects>`_
    for the usage.

    """

    ColorPrefix: Dict[int, str] = {
        0: "\x1b[0m",
        10: "\x1b[35m",
        20: "\x1b[32m",
        30: "\x1b[33m",
        40: "\x1b[31m",
        50: "\x1b[41;97m",
    }

    def format(self, record: logging.LogRecord) -> logging.LogRecord:
        """Format a record to text."""
        levelno = int(utils.clip(record.levelno // 10 * 10, 0, 50))
        original_levelname = record.levelname
        record.levelname = self.ColorPrefix[levelno] + original_levelname + "\x1b[0m"
        return super().format(record)
