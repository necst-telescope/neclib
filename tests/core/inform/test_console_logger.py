import logging

import pytest

from neclib.core import get_logger

logger_name = "neclib.test"


def test_get_logger():
    logger = get_logger(logger_name)
    assert logger.name == "necst." + logger_name
    assert get_logger(logger_name) is logger


@pytest.fixture
def logger() -> logging.Logger:
    return get_logger(logger_name)


@pytest.fixture
def debug_logger() -> logging.Logger:
    return get_logger(logger_name, min_level=logging.DEBUG)


class TestLogger:

    this_file_name = __file__.split("/")[-1]

    def test_debug(
        self, caplog: pytest.LogCaptureFixture, debug_logger: logging.Logger
    ):
        with caplog.at_level(logging.DEBUG):
            debug_logger.debug("DEBUG level message")
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
