from pathlib import Path

import necstdb
import pytest

from neclib.interfaces import get_logger
from neclib.interfaces.console_logger import ConsoleLogger
from neclib.recorders import ConsoleLogWriter, NECSTDBWriter, Recorder


@pytest.fixture
def logger() -> ConsoleLogger:
    return get_logger("test")


class TestRecorder:
    def test_single_writer(self, data_root: Path):
        recorder = Recorder(data_root)
        recorder.add_writer(NECSTDBWriter())

        recorder.start_recording("test.necstdb")

        assert len(recorder.writers) == 1
        recorder.append("test", [{"key": "time", "type": "int32", "value": 4}])
        db_path: Path = recorder.writers[0].db.path

        recorder.stop_recording()

        assert db_path.resolve() == data_root / "test.necstdb"
        assert necstdb.opendb(db_path).open_table("test").read(astype="sa")["time"] == 4

    def test_multiple_writer(self, data_root: Path, logger: ConsoleLogger):
        recorder = Recorder(data_root)
        recorder.add_writer(NECSTDBWriter(), ConsoleLogWriter())

        recorder.start_recording("test.necstdb")

        assert len(recorder.writers) == 2
        recorder.append("test", [{"key": "time", "type": "int32", "value": 4}])
        logger.error("Error message")
        db_path: Path = recorder.writers[0].db.path
        log_path: Path = recorder.writers[1].log_file_path

        recorder.stop_recording()

        assert db_path.resolve() == data_root / "test.necstdb"
        assert necstdb.opendb(db_path).open_table("test").read(astype="sa")["time"] == 4

        assert log_path.resolve() == data_root / "test.necstdb" / "console.log"
        assert "Error message" in log_path.read_text()

    def test_absolute_path(self, data_root: Path, logger: ConsoleLogger):
        recorder = Recorder(data_root)
        recorder.add_writer(ConsoleLogWriter())

        recorder.start_recording(data_root / "test")  # Full path

        assert len(recorder.writers) == 1
        logger.info("Info message")
        log_path: Path = recorder.writers[0].log_file_path

        recorder.stop_recording()

        assert log_path.resolve() == data_root / "test" / "console.log"
        assert "Info message" in log_path.read_text()

    def test_just_warn_unrecorded(self, data_root: Path, capsys: pytest.CaptureFixture):
        recorder = Recorder(data_root)
        recorder.add_writer(ConsoleLogWriter())
        recorder.start_recording("test.necstdb")
        recorder.append("test", [{"key": "time", "type": "int32", "value": 4}])
        recorder.stop_recording()

        captured = capsys.readouterr()  # caplog does not capture intended log
        assert "No writer handled the data" in captured.err
