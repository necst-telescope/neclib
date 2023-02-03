"""TOML file handling."""

import os
from typing import IO, Any, Dict, Mapping, Union

from tomlkit import TOMLDocument, dumps, parse
from tomlkit.items import Table

from .general import read as read_file


def read(__file: Union[os.PathLike, str, IO], /) -> TOMLDocument:
    r"""Read and parse a TOML file.

    Parameters
    ----------
    __file
        Path to the TOML file or a file-like object.

    Returns
    -------
    parsed
        The parsed content.

    Examples
    --------
    >>> neclib.core.toml.read("path/to/pyproject.toml")

    You can also pass a file-like object:

    >>> with open("pyproject.toml") as f:
    ...     neclib.core.toml.read(f)

    """
    return parse(read_file(__file))


def flatten(
    doc: Dict[str, Any], /, *, prefix: str = "", sep: str = "."
) -> TOMLDocument:
    """Flatten a parsed TOML object.

    Parameters
    ----------
    doc
        TOML document or TOML Table to be flattened.
    prefix
        Prefix to be added to the keys.
    sep
        Separator to be used to join keys.

    Returns
    -------
    flattened
        The flattened TOML document.

    Notes
    -----
    This function flattens dict-like objects recursively, but ``InlineTable`` objects
    will be kept as is. This feature comes from the following motivations:

    - TOML files should be well-structured by the parameters semantics.
    - Deeply nested dict-like object is hard to handle, so we flatten them.
    - Flattening all dict-like objects will remove ability to store
      structured-parameter (dict-like object) in TOML files.

    The author never felt this implementation a good one, since it contradicts the TOML
    specification: "inline-tables are just a short-hand definition of tables", which
    implies they should be treated equivalently. If the alternative method to flatten
    TOML document is found, this function will employ it.

    Examples
    --------
    >>> neclib.core.toml.flatten({"a": {"b": 1, "c": 2}, "d": 3})
    {"a.b": 1, "a.c": 2, "d": 3}

    """
    ret = TOMLDocument()
    prefix = prefix + sep if prefix else ""
    for k, v in doc.items():
        if isinstance(v, Table):
            ret.update(flatten(v, prefix=prefix + k))
        else:
            ret.update({prefix + k: v})
    return ret


def to_string(__mapping: Mapping[str, Any], /) -> str:
    r"""Convert a mapping to a TOML string.

    Parameters
    ----------
    __mapping
        Mapping object to be converted.

    Returns
    -------
    toml_string
        TOML format representation of given mapping object.

    Examples
    --------
    >>> neclib.core.toml.to_string({"a": 1, "b": 2})
    'a = 1\nb = 2'

    """
    return dumps(__mapping)
