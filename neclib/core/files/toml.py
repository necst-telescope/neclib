import os
from typing import IO, Any, Dict, Mapping, Union

from tomlkit import TOMLDocument, dumps, parse
from tomlkit.items import Table

from .general import read as read_file


def read(__file: Union[os.PathLike, str, IO], /) -> TOMLDocument:
    file_path = isinstance(__file, (os.PathLike, str))
    return parse(read_file(__file) if file_path else __file.read())


def flatten(doc: Dict[str, Any], /, *, prefix: str = "") -> TOMLDocument:
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
