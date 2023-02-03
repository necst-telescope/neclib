from logging import Logger
from pathlib import Path

import pytest

from neclib.core import get_logger
from neclib.recorders import ConsoleLogWriter


@pytest.fixture
def logger() -> Logger:
    return get_logger("test")


class TestConsoleLogWriter:
    def test_single_log(self, data_root: Path, logger: Logger):
        writer = ConsoleLogWriter()

        writer.start_recording(data_root)
        logger.debug("DEBUG level message")
        logfile = writer.log_file_path
        writer.stop_recording()

        assert logfile.read_text().count("DEBUG level message") == 1

    def test_multiple_logs(self, data_root: Path, logger: Logger):
        writer = ConsoleLogWriter()

        writer.start_recording(data_root)
        logger.info("INFO level message")
        logger.warning("WARNING level message")
        logfile = writer.log_file_path
        writer.stop_recording()

        assert logfile.read_text().count("INFO level message") == 1
        assert logfile.read_text().count("WARNING level message") == 1

    def test_log_before_start_recording(self, data_root: Path, logger: Logger):
        writer = ConsoleLogWriter()

        logger.error("ERROR level message")

        writer.start_recording(data_root)
        logger.error("ERROR level message")
        logfile = writer.log_file_path
        writer.stop_recording()

        assert logfile.read_text().count("ERROR level message") == 1

    def test_log_after_stop_recording(self, data_root: Path, logger: Logger):
        writer = ConsoleLogWriter()

        writer.start_recording(data_root)
        logger.obslog("OBSERVATION log")
        logger.critical("CRITICAL level message")
        logfile = writer.log_file_path
        obslogfile = writer.obslog_file_path
        writer.stop_recording()

        logger.obslog("OBSERVATION log")
        logger.critical("CRITICAL level message")

        assert obslogfile.read_text().count("OBSERVATION log") == 1
        assert logfile.read_text().count("CRITICAL level message") == 1

    def test_reuse(self, data_root: Path, logger: Logger):
        writer = ConsoleLogWriter()

        writer.start_recording(data_root / "db1")
        logger.info("INFO level message")
        logfile1 = writer.log_file_path
        writer.stop_recording()

        writer.start_recording(data_root / "db2")
        logger.info("INFO level message")
        logger.warning("WARNING level message")
        logfile2 = writer.log_file_path
        writer.stop_recording()

        assert logfile1.read_text().count("INFO level message") == 1

        assert logfile2.read_text().count("INFO level message") == 1
        assert logfile2.read_text().count("WARNING level message") == 1
