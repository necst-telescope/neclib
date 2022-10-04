import time
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

        def read_first_data(table_name: str):
            return db.open_table(table_name).read(astype="sa")["data"][0]

        assert read_first_data("topic01") == True  # noqa: E712
        assert read_first_data("topic02") == b"abc"
        assert read_first_data("topic03") == b"c"
        assert read_first_data("topic04") == pytest.approx(3.2)
        assert read_first_data("topic05") == pytest.approx(0.32)
        assert read_first_data("topic06") == pytest.approx(6.4)
        assert read_first_data("topic07") == pytest.approx(0.64)
        assert read_first_data("topic08") == -8
        assert read_first_data("topic09") == -16
        assert read_first_data("topic10") == -32
        assert read_first_data("topic11") == -64
        assert read_first_data("topic12") == 8
        assert read_first_data("topic13") == 16
        assert read_first_data("topic14") == 32
        assert read_first_data("topic15") == 64
        assert read_first_data("topic16") == b"abcde"  # Caution not str

    def test_array_data(self, data_root: Path):
        writer = DBWriter(data_root)

        writer.start_recording()
        bool_ = [True, False]
        bytes_ = [b"abc", b"def"]
        char_ = [b"a", b"b"]
        float_ = [3.2, 4.3]
        double_ = [6.4, 7.5]
        int8_ = [-8, 8]
        int16_ = [-16, 16]
        int32_ = [-32, 32]
        int64_ = [-64, 64]
        uint8_ = [7, 8]
        uint16_ = [15, 16]
        uint32_ = [31, 32]
        uint64_ = [63, 64]
        string_ = ["abc", "def"]

        writer.append("topic01", [{"key": "data", "type": "bool", "value": bool_}])
        writer.append("topic02", [{"key": "data", "type": "byte", "value": bytes_}])
        writer.append("topic03", [{"key": "data", "type": "char", "value": char_}])
        writer.append("topic04", [{"key": "data", "type": "float32", "value": float_}])
        writer.append("topic05", [{"key": "data", "type": "float", "value": float_}])
        writer.append("topic06", [{"key": "data", "type": "float64", "value": double_}])
        writer.append("topic07", [{"key": "data", "type": "double", "value": double_}])
        writer.append("topic08", [{"key": "data", "type": "int8", "value": int8_}])
        writer.append("topic09", [{"key": "data", "type": "int16", "value": int16_}])
        writer.append("topic10", [{"key": "data", "type": "int32", "value": int32_}])
        writer.append("topic11", [{"key": "data", "type": "int64", "value": int64_}])
        writer.append("topic12", [{"key": "data", "type": "uint8", "value": uint8_}])
        writer.append("topic13", [{"key": "data", "type": "uint16", "value": uint16_}])
        writer.append("topic14", [{"key": "data", "type": "uint32", "value": uint32_}])
        writer.append("topic15", [{"key": "data", "type": "uint64", "value": uint64_}])
        writer.append("topic16", [{"key": "data", "type": "string", "value": string_}])
        db_path = writer.db.path
        writer.stop_recording()

        db = necstdb.opendb(db_path)

        def read_first_data(table_name: str):
            return db.open_table(table_name).read(astype="sa")["data"][0]

        assert (read_first_data("topic01") == bool_).all()
        assert (read_first_data("topic02") == bytes_).all()
        assert (read_first_data("topic03") == char_).all()
        assert read_first_data("topic04") == pytest.approx(float_)
        assert read_first_data("topic05") == pytest.approx(float_)
        assert read_first_data("topic06") == pytest.approx(double_)
        assert read_first_data("topic07") == pytest.approx(double_)
        assert (read_first_data("topic08") == int8_).all()
        assert (read_first_data("topic09") == int16_).all()
        assert (read_first_data("topic10") == int32_).all()
        assert (read_first_data("topic11") == int64_).all()
        assert (read_first_data("topic12") == uint8_).all()
        assert (read_first_data("topic13") == uint16_).all()
        assert (read_first_data("topic14") == uint32_).all()
        assert (read_first_data("topic15") == uint64_).all()
        assert (read_first_data("topic16") == bytes_).all()  # Caution not str

    def test_close_inactive_table(self, data_root: Path):
        DBWriter.LivelinessDuration = 0.5
        writer = DBWriter(data_root)

        writer.start_recording()
        writer.append("topic1", [{"key": "time", "type": "string", "value": "abc"}])
        time.sleep(1)
        assert writer.tables == {}
        writer.stop_recording()

    @pytest.mark.xfail(reason="Impl. of necstdb doesn't support OTF data size change")
    def test_string_completeness(self, data_root: Path):
        writer = DBWriter(data_root)

        writer.start_recording()
        writer.append("topic1", [{"key": "time", "type": "string", "value": "abc"}])
        writer.append("topic1", [{"key": "time", "type": "string", "value": "abcde"}])
        db_path = writer.db.path
        writer.stop_recording()

        db = necstdb.opendb(db_path)
        data = db.open_table("topic1").read(astype="sa")
        assert (data["time"] == ["abc", "abcde"]).all()
