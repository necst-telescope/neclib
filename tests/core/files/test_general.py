from http.server import HTTPServer
from pathlib import Path

from neclib.core import read


class TestRead:
    def test_read_path(self, data_dir: Path) -> None:
        assert read(data_dir / "sample_toml_file.toml").startswith("int_param = 1")

    def test_read_str_path(self, data_dir: Path) -> None:
        assert read(str(data_dir / "sample_toml_file.toml")).startswith("int_param = 1")

    def test_read_io(self, data_dir: Path) -> None:
        with (data_dir / "sample_toml_file.toml").open("r") as f:
            assert read(f).startswith("int_param = 1")

    def test_read_file_uri(self, data_dir: Path) -> None:
        uri = f"file://{data_dir / 'sample_toml_file.toml'}"
        assert read(uri).startswith("int_param = 1")

    def test_read_remote_file(self, data_dir: Path, httpserver: HTTPServer) -> None:
        response = read(data_dir / "sample_toml_file.toml")
        httpserver.expect_request("/sample_toml_file.toml").respond_with_data(
            response, content_type="text/plain"
        )

        assert read(httpserver.url_for("/sample_toml_file.toml")).startswith(
            "int_param = 1"
        )
