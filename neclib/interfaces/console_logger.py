__all__ = ["getLogger"]

import logging
from typing import Dict

from .. import utils
from ..typing import PathLike


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

    def format(self, record: logging.LogRecord) -> logging.LogRecord:
        """Format a record to text."""
        levelno = int(utils.clip(record.levelno // 10 * 10, 0, 50))
        original_levelname = record.levelname
        record.levelname = self.ColorPrefix[levelno] + original_levelname + "\x1b[0m"
        return super().format(record)


class ConsoleLogger(logging.Logger):

    OBSERVE_level = logging.INFO + 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        logging.addLevelName(self.OBSERVE_level, "OBSERVE")

    def obslog(self, msg, indent_level: int = 0, *args, **kwargs):
        """Log observation summary.

        Argument other than ``indent_level`` are interpreted as for
        `logging.Logger.debug <https://docs.python.org/3/library/logging.html#logging.Logger.debug>`_

        indent_level
            If non-zero, this message is logged with indentation.

        """  # noqa: E501
        indented_msg = "    " * indent_level + msg
        super()._log(self.OBSERVE_level, indented_msg, args, **kwargs)


def getLogger(
    name: str,
    file_path: PathLike,
    obslog_file_path: PathLike,
    min_level: int = logging.DEBUG,
) -> ConsoleLogger:
    """Get logger instance which prints operation logs to console and dumps to file.

    Parameters
    ----------
    name
        Name of the logger. Calling this function with same ``name`` returns the same
        logger instance.
    file_path
        Path to file into which all logs (severity >= ``logging.DEBUG``) are dumped.
    obslog_file_path
        Path to file to log observation summary.
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
    logging.setLoggerClass(ConsoleLogger)
    logger = logging.getLogger("necst." + name)
    rootLogger = logging.getLogger()

    fmt = "%(asctime)-s: [%(levelname)-s: %(filename)s#L%(lineno)s] %(message)s"
    color_log_format = ColorizeLevelNameFormatter(fmt)
    text_log_format = logging.Formatter(fmt)
    obslog_file_format = logging.Formatter("- [(UTC) %(asctime)-s] %(message)s")

    fh = logging.FileHandler(file_path)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(text_log_format)

    obs_fh = logging.FileHandler(obslog_file_path)
    obs_fh.addFilter(lambda record: record.levelno == ConsoleLogger.OBSERVE_level)
    obs_fh.setFormatter(obslog_file_format)

    ch = logging.StreamHandler()
    ch.setLevel(min_level)
    ch.setFormatter(color_log_format)

    rootLogger.setLevel(logging.DEBUG)
    rootLogger.handlers.clear()  # Avoid duplicate handlers to be set.
    rootLogger.addHandler(fh)
    rootLogger.addHandler(obs_fh)
    rootLogger.addHandler(ch)

    return logger
