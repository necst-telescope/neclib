import logging
from pathlib import Path
from typing import Optional

from .writer_base import Writer
from ..interfaces.console_logger import ConsoleLogger


class ConsoleLogWriter(Writer):
    """Record writer for console log.

    Attributes
    ----------
    log_file_path
        Path to file into which all logs (severity >= ``logging.DEBUG``) are dumped.
    obslog_file_path
        Path to file to log observation summary.

    """

    def __init__(self) -> None:
        fmt = "%(asctime)-s: [%(levelname)-s: %(filename)s#L%(lineno)s] %(message)s"
        self.log_format = logging.Formatter(fmt)
        self.obslog_format = logging.Formatter("- [(UTC) %(asctime)-s] %(message)s")

        self.log_file_path: Optional[Path] = None
        self.obslog_file_path: Optional[Path] = None

    def start_recording(self, record_dir: Path) -> None:
        record_dir.mkdir(parents=True, exist_ok=True)

        self.log_file_path = record_dir / "console.log"
        self.obslog_file_path = record_dir / "observation.log"

        self.fh = logging.FileHandler(self.log_file_path)
        self.fh.setLevel(logging.DEBUG)
        self.fh.setFormatter(self.log_format)

        self.obs_fh = logging.FileHandler(self.obslog_file_path)
        self.obs_fh.addFilter(
            lambda record: record.levelno == ConsoleLogger.OBSERVE_level
        )
        self.obs_fh.setFormatter(self.obslog_format)

        rootLogger = logging.getLogger()
        rootLogger.addHandler(self.fh)
        rootLogger.addHandler(self.obs_fh)

    def append(self, *args, **kwargs) -> bool:
        """This writer don't accept any data not issued by ``logging.Logger``."""
        return False

    def stop_recording(self) -> None:
        self.log_file_path = None
        self.obslog_file_path = None

        rootLogger = logging.getLogger()
        rootLogger.removeHandler(self.fh)
        rootLogger.removeHandler(self.obs_fh)
