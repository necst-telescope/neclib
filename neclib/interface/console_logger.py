__all__ = ["getLogger", "ColorizeLevelNameFormatter"]

import logging
from typing import Dict

from .. import utils
from ..typing import PathLike


def getLogger(
    name: str, file_path: PathLike, min_level: int = logging.DEBUG
) -> logging.Logger:
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
    """Colorize severity level name."""

    Colors: Dict[int, str] = {
        0: "\x1b[0m",
        10: "\x1b[35m",
        20: "\x1b[32m",
        30: "\x1b[33m",
        40: "\x1b[31m",
        50: "\x1b[41;97m",
    }

    def format(self, record: logging.LogRecord) -> logging.LogRecord:
        levelno = int(utils.clip(record.levelno // 10 * 10, 0, 50))
        original_levelname = record.levelname
        record.levelname = self.Colors[levelno] + original_levelname + "\x1b[0m"
        return super().format(record)
