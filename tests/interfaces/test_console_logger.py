import logging
from pathlib import Path

import pytest

from neclib.interface import getLogger


@pytest.fixture(scope="module")
def tmp_log_dir(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("log")


logger_name = "neclib.test"
logfile_name = "test_log.txt"


def test_getLogger(tmp_log_dir):
    logger = getLogger(logger_name, tmp_log_dir / logfile_name)
    assert logger.name == logger_name
    assert getLogger(logger_name, tmp_log_dir / logfile_name) is logger


@pytest.fixture(scope="module")
def logger(tmp_log_dir) -> logging.Logger:
    return getLogger(logger_name, tmp_log_dir / logfile_name)


class Test:

    logger_name = "neclib.test"
    logfile_name = "test_log.txt"

    this_file_name = __file__.split("/")[-1]

    def test_debug(self, caplog: pytest.LogCaptureFixture, logger: logging.Logger):
        with caplog.at_level(logging.DEBUG):
            logger.debug("DEBUG level message")
            assert ["DEBUG level message"] == [rec.message for rec in caplog.records]
            assert [logging.DEBUG] == [rec.levelno for rec in caplog.records]
            assert ["\x1b[35mDEBUG\x1b[0m"] == [rec.levelname for rec in caplog.records]
            assert [self.this_file_name] == [rec.filename for rec in caplog.records]

    def test_info(self, caplog: pytest.LogCaptureFixture, logger: logging.Logger):
        with caplog.at_level(logging.DEBUG):
            logger.info("INFO level message")
            assert ["INFO level message"] == [rec.message for rec in caplog.records]
            assert [logging.INFO] == [rec.levelno for rec in caplog.records]
            assert ["\x1b[32mINFO\x1b[0m"] == [rec.levelname for rec in caplog.records]
            assert [self.this_file_name] == [rec.filename for rec in caplog.records]

    def test_warning(self, caplog: pytest.LogCaptureFixture, logger: logging.Logger):
        with caplog.at_level(logging.DEBUG):
            logger.warning("WARNING level message")
            assert ["WARNING level message"] == [rec.message for rec in caplog.records]
            assert [logging.WARNING] == [rec.levelno for rec in caplog.records]
            assert ["\x1b[33mWARNING\x1b[0m"] == [
                rec.levelname for rec in caplog.records
            ]
            assert [self.this_file_name] == [rec.filename for rec in caplog.records]

    def test_error(self, caplog: pytest.LogCaptureFixture, logger: logging.Logger):
        with caplog.at_level(logging.DEBUG):
            logger.error("ERROR level message")
            assert ["ERROR level message"] == [rec.message for rec in caplog.records]
            assert [logging.ERROR] == [rec.levelno for rec in caplog.records]
            assert ["\x1b[31mERROR\x1b[0m"] == [rec.levelname for rec in caplog.records]
            assert [self.this_file_name] == [rec.filename for rec in caplog.records]

    def test_critical(self, caplog: pytest.LogCaptureFixture, logger: logging.Logger):
        with caplog.at_level(logging.DEBUG):
            logger.critical("CRITICAL level message")
            assert ["CRITICAL level message"] == [rec.message for rec in caplog.records]
            assert [logging.CRITICAL] == [rec.levelno for rec in caplog.records]
            assert ["\x1b[41;97mCRITICAL\x1b[0m"] == [
                rec.levelname for rec in caplog.records
            ]
            assert [self.this_file_name] == [rec.filename for rec in caplog.records]

    def test_msg_args(self, caplog: pytest.LogCaptureFixture, logger: logging.Logger):
        with caplog.at_level(logging.DEBUG):
            logger.warning("test message")
            msg = "test message"
            logger.warning("%s", msg)
            assert [msg, msg] == [rec.message for rec in caplog.records]

    def test_file(self, tmp_log_dir: Path):
        record_txt = (tmp_log_dir / self.logfile_name).read_text()
        assert record_txt.count("DEBUG level message") == 1
        assert record_txt.count("INFO level message") == 1
        assert record_txt.count("WARNING level message") == 1
        assert record_txt.count("ERROR level message") == 1
        assert record_txt.count("CRITICAL level message") == 1

        # 5 tests [debug,info,warning,error,critical] will certainly be done.
        assert record_txt.count(self.this_file_name) >= 5
