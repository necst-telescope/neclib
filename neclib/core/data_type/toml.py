import os
from typing import IO, Any, Mapping, Union

from tomlkit import TOMLDocument, dumps, parse
from tomlkit.items import Table
from tomlkit.toml_file import TOMLFile


def read(__file: Union[os.PathLike, str, IO], /) -> TOMLDocument:
    file_path = isinstance(__file, (os.PathLike, str))
    return TOMLFile(__file).read() if file_path else parse(__file.read())


def flatten(doc: TOMLDocument, /, *, prefix: str = "") -> TOMLDocument[str, Any]:
    ret = TOMLDocument()
    prefix = prefix + "." if prefix else ""
    for k, v in doc.items():
        if isinstance(v, Table):
            ret.update(flatten(v, prefix=prefix + k))
        else:
            ret.update({prefix + k: v})
    return ret


def to_string(__mapping: Mapping[str, Any], /) -> str:
    return dumps(__mapping)
