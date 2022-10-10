from pathlib import Path

from neclib.recorders import FileWriter


class TestFileWriter:
    def test_single_file(self, data_root: Path):
        writer = FileWriter()

        writer.start_recording(data_root)
        writer.append("test.txt", "test contents")
        writer.stop_recording()

        recorded = (data_root / "test.txt").read_text()
        assert "# Original file: test.txt\n# Recorded time:" in recorded
        assert "test contents" in recorded

    def test_multiple_files(self, data_root: Path):
        writer = FileWriter()

        writer.start_recording(data_root)
        writer.append("test.txt", "test contents")
        writer.append("172.20.101.15:/home/user/test.py", "test contents")
        writer.stop_recording()

        recorded1 = (data_root / "test.txt").read_text()
        assert "# Original file: test.txt\n# Recorded time:" in recorded1
        assert "test contents" in recorded1

        recorded2 = (data_root / "test.py").read_text()
        assert (
            "# Original file: 172.20.101.15:/home/user/test.py\n# Recorded time:"
            in recorded2
        )
        assert "test contents" in recorded2

    def test_same_filename(self, data_root: Path):
        writer = FileWriter()

        writer.start_recording(data_root)
        writer.append("test.txt", "test contents")
        writer.append("/home/user/test.txt", "different contents")
        writer.stop_recording()

        recorded1 = (data_root / "test.txt").read_text()
        assert "# Original file: test.txt\n# Recorded time:" in recorded1
        assert "test contents" in recorded1

        recorded2 = (data_root / "test(1).txt").read_text()
        assert "# Original file: /home/user/test.txt\n# Recorded time:" in recorded2
        assert "different contents" in recorded2

    def test_record_before_start_recording(self, data_root: Path):
        writer = FileWriter()

        writer.append("test.txt", "lost contents")

        writer.start_recording(data_root)
        writer.append("test.txt", "test contents")
        writer.stop_recording()

        recorded = (data_root / "test.txt").read_text()
        assert "# Original file: test.txt\n# Recorded time:" in recorded
        assert "test contents" in recorded

    def test_record_after_stop_recording(self, data_root: Path):
        writer = FileWriter()

        writer.start_recording(data_root)
        writer.append("test.txt", "test contents")
        writer.stop_recording()

        writer.append("test.txt", "lost contents")

        recorded = (data_root / "test.txt").read_text()
        assert "# Original file: test.txt\n# Recorded time:" in recorded
        assert "test contents" in recorded

    def test_reuse(self, data_root: Path):
        writer = FileWriter()

        writer.start_recording(data_root / "db1")
        writer.append("test.txt", "test contents")
        writer.stop_recording()

        writer.start_recording(data_root / "db2")
        writer.append("test.txt", "different contents")
        writer.stop_recording()

        recorded1 = (data_root / "db1" / "test.txt").read_text()
        assert "# Original file: test.txt\n# Recorded time:" in recorded1
        assert "test contents" in recorded1

        recorded2 = (data_root / "db2" / "test.txt").read_text()
        assert "# Original file: test.txt\n# Recorded time:" in recorded2
        assert "different contents" in recorded2
