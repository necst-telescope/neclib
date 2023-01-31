from pathlib import Path

from tomlkit import parse

from neclib.core import toml


def test_read(data_dir: Path) -> None:
    from_path = toml.read(data_dir / "sample_toml_file.toml")
    from_str = toml.read(str(data_dir / "sample_toml_file.toml"))
    with (data_dir / "sample_toml_file.toml").open("r") as f:
        from_file = toml.read(f)
    assert from_path == from_str
    assert from_path == from_file


class TestFlatten:
    def test_flatten(self) -> None:
        toml_str = """
        [package]
        name = "neclib"
        version = "0.1.0"
        "weight[kg]" = 0.1
        [package.metadata]
        authors = ["John Doe"]
        required = true
        """
        doc = parse(toml_str)
        flattened = toml.flatten(doc)
        assert flattened["package.name"] == "neclib"
        assert flattened["package.version"] == "0.1.0"
        assert flattened["package.weight[kg]"] == 0.1
        assert flattened["package.metadata.authors"] == ["John Doe"]
        assert flattened["package.metadata.required"] is True

    def test_keep_inline_table(self) -> None:
        toml_str = """
        [package]
        name = "neclib"
        [package.metadata]
        neclib = {version = "0.1.0"}
        """
        doc = parse(toml_str)
        flattened = toml.flatten(doc)
        assert flattened["package.name"] == "neclib"
        assert flattened["package.metadata.neclib"] == {"version": "0.1.0"}


def test_to_string() -> None:
    m = {"a": 1, "b": 2.1}
    assert toml.to_string(m).strip() == "a = 1\nb = 2.1"

    m = {"a": [1, 2], "b": True}
    assert toml.to_string(m).strip() == "a = [1, 2]\nb = true"

    m = {"a": {"b": 1, "c": 2}}
    assert toml.to_string(m).strip() == "[a]\nb = 1\nc = 2"
