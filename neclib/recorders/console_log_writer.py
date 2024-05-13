import logging
from pathlib import Path
from typing import Optional

from .writer_base import Writer


class ConsoleLogWriter(Writer):
    """Record writer for console log.

    Attributes
    ----------
    log_file_path
        Path to file into which all logs (severity >= ``logging.DEBUG``) are dumped.

    """

    def __init__(self) -> None:
        if not self._initialized[self.__class__]:
            fmt = "%(asctime)-s: [%(levelname)-s: %(filename)s#L%(lineno)s] %(message)s"
            self.log_format = logging.Formatter(fmt)

            self.log_file_path: Optional[Path] = None

            self._initialized[self.__class__] = True

    def start_recording(self, record_dir: Path) -> None:
        record_dir.mkdir(parents=True, exist_ok=True)

        self.log_file_path = record_dir / "console.log"

        self.fh = logging.FileHandler(self.log_file_path)
        self.fh.setLevel(logging.DEBUG)
        self.fh.setFormatter(self.log_format)

        rootLogger = logging.getLogger()
        rootLogger.addHandler(self.fh)

    def append(self, *args, **kwargs) -> bool:
        """This writer don't accept any data not issued by ``logging.Logger``."""
        return False

    def stop_recording(self) -> None:
        self.log_file_path = None

        rootLogger = logging.getLogger()
        rootLogger.removeHandler(self.fh)
