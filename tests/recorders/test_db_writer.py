from pathlib import Path

import necstdb
import pytest

from neclib.recorders import DBWriter


@pytest.fixture
def data_root(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("data")


class TestDBWriter:
    def test_single_topic_single_data(self, data_root: Path):
        writer = DBWriter(data_root)

        writer.start_recording()
        writer.append("topic1", [{"key": "time", "type": "int32", "value": 5}])
        db_path = writer.db.path
        writer.stop_recording()

        db = necstdb.opendb(db_path)
        data = db.open_table("topic1").read(astype="sa")
        assert data["time"] == 5

    def test_single_topic_multiple_data(self, data_root: Path):
        writer = DBWriter(data_root)

        writer.start_recording()
        writer.append("topic1", [{"key": "time", "type": "int32", "value": 5}])
        writer.append("topic1", [{"key": "time", "type": "int32", "value": 4}])
        db_path = writer.db.path
        writer.stop_recording()

        db = necstdb.opendb(db_path)
        data = db.open_table("topic1").read(astype="sa")
        assert (data["time"] == [5, 4]).all()

    def test_multiple_topic_single_data(self, data_root: Path):
        writer = DBWriter(data_root)

        writer.start_recording()
        writer.append("topic1", [{"key": "time", "type": "int32", "value": 5}])
        writer.append("topic2", [{"key": "time", "type": "int32", "value": 4}])
        db_path = writer.db.path
        writer.stop_recording()

        db = necstdb.opendb(db_path)
        data1 = db.open_table("topic1").read(astype="sa")
        assert data1["time"] == 5
        data2 = db.open_table("topic2").read(astype="sa")
        assert data2["time"] == 4

    def test_multiple_topic_multiple_data(self, data_root: Path):
        writer = DBWriter(data_root)

        writer.start_recording()
        writer.append("topic1", [{"key": "time", "type": "int32", "value": 5}])
        writer.append("topic2", [{"key": "time", "type": "int32", "value": 4}])
        writer.append("topic1", [{"key": "time", "type": "int32", "value": 3}])
        writer.append("topic2", [{"key": "time", "type": "int32", "value": 2}])
        db_path = writer.db.path
        writer.stop_recording()

        db = necstdb.opendb(db_path)
        data1 = db.open_table("topic1").read(astype="sa")
        assert (data1["time"] == [5, 3]).all()
        data2 = db.open_table("topic2").read(astype="sa")
        assert (data2["time"] == [4, 2]).all()

    def test_invalid_name(self, data_root: Path):
        writer = DBWriter(data_root)

        writer.start_recording()
        writer.append("/topic1", [{"key": "time", "type": "int32", "value": 5}])
        db_path = writer.db.path
        writer.stop_recording()

        db = necstdb.opendb(db_path)
        data = db.open_table("topic1").read(astype="sa")
        assert data["time"] == 5

    def test_append_before_start_recording(self, data_root: Path):
        writer = DBWriter(data_root)
        writer.append("topic1", [{"key": "time", "type": "int32", "value": 5}])

        writer.start_recording()
        db_path = writer.db.path
        writer.stop_recording()

        db = necstdb.opendb(db_path)
        assert db.list_tables() == []

    def test_append_after_start_recording(self, data_root: Path):
        writer = DBWriter(data_root)

        writer.start_recording()
        db_path = writer.db.path
        writer.stop_recording()

        writer.append("topic1", [{"key": "time", "type": "int32", "value": 5}])

        db = necstdb.opendb(db_path)
        assert db.list_tables() == []

    def test_reuse(self, data_root: Path):
        writer = DBWriter(data_root)

        writer.start_recording()
        writer.append("topic1", [{"key": "time", "type": "int32", "value": 5}])
        db_path = writer.db.path
        writer.stop_recording()

        db = necstdb.opendb(db_path)
        data = db.open_table("topic1").read(astype="sa")
        assert data["time"] == 5

        writer.start_recording("test_db")
        writer.append("topic1", [{"key": "time", "type": "int32", "value": 4}])
        db_path = writer.db.path
        writer.stop_recording()

        db = necstdb.opendb(db_path)
        data = db.open_table("topic1").read(astype="sa")
        assert data["time"] == 4

    def test_data_types(self, data_root: Path):
        writer = DBWriter(data_root)

        writer.start_recording()
        writer.append("topic01", [{"key": "data", "type": "bool", "value": True}])
        writer.append("topic02", [{"key": "data", "type": "byte", "value": b"abc"}])
        writer.append("topic03", [{"key": "data", "type": "char", "value": b"c"}])
        writer.append("topic04", [{"key": "data", "type": "float32", "value": 3.2}])
        writer.append("topic05", [{"key": "data", "type": "float", "value": 0.32}])
        writer.append("topic06", [{"key": "data", "type": "float64", "value": 6.4}])
        writer.append("topic07", [{"key": "data", "type": "double", "value": 0.64}])
        writer.append("topic08", [{"key": "data", "type": "int8", "value": -8}])
        writer.append("topic09", [{"key": "data", "type": "int16", "value": -16}])
        writer.append("topic10", [{"key": "data", "type": "int32", "value": -32}])
        writer.append("topic11", [{"key": "data", "type": "int64", "value": -64}])
        writer.append("topic12", [{"key": "data", "type": "uint8", "value": 8}])
        writer.append("topic13", [{"key": "data", "type": "uint16", "value": 16}])
        writer.append("topic14", [{"key": "data", "type": "uint32", "value": 32}])
        writer.append("topic15", [{"key": "data", "type": "uint64", "value": 64}])
        writer.append("topic16", [{"key": "data", "type": "string", "value": "abcde"}])
        db_path = writer.db.path
        writer.stop_recording()

        db = necstdb.opendb(db_path)
        assert db.open_table("topic01").read(astype="sa")["data"] == True  # noqa: E712
        assert db.open_table("topic02").read(astype="sa")["data"] == b"abc"
        assert db.open_table("topic03").read(astype="sa")["data"] == b"c"
        assert db.open_table("topic04").read(astype="sa")["data"] == 3.2
        assert db.open_table("topic05").read(astype="sa")["data"] == 0.32
        assert db.open_table("topic06").read(astype="sa")["data"] == 6.4
        assert db.open_table("topic07").read(astype="sa")["data"] == 0.64
        assert db.open_table("topic08").read(astype="sa")["data"] == -8
        assert db.open_table("topic09").read(astype="sa")["data"] == -16
        assert db.open_table("topic10").read(astype="sa")["data"] == -32
        assert db.open_table("topic11").read(astype="sa")["data"] == -64
        assert db.open_table("topic12").read(astype="sa")["data"] == 8
        assert db.open_table("topic13").read(astype="sa")["data"] == 16
        assert db.open_table("topic14").read(astype="sa")["data"] == 32
        assert db.open_table("topic15").read(astype="sa")["data"] == 64
        assert db.open_table("topic16").read(astype="sa")["data"] == b"abcde"  # Not str
