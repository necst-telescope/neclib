from neclib.utils import read_file


class TestReadFile:
    def test_read_text(self, data_dir):
        assert read_file(data_dir / "sample_config_customized.toml").startswith(
            'observatory = "NANTEN2"'
        )
