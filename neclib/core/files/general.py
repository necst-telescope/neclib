"""General file operations.

This module provides general file operations, not limited to a specific file format or
method to access the file system.

"""

__all__ = ["read"]

import os
from pathlib import Path
from typing import IO, Union
from urllib.parse import urlparse
from urllib.request import urlopen


def read(__path: Union[os.PathLike, str, IO], /, *, allow_remote: bool = True) -> str:
    """Read a file, if it's accessible via any available way.

    Parameters
    ----------
    __path
        The file path.
    allow_remote
        If True the file can be fetched from remote host, otherwise the look-up is
        limited to local file system.

    Returns
    -------
    content
        The file content.

    Raises
    ------
    FileNotFoundError
        If the file couldn't be found.
    URLError
        If the protocol (http, https, ftp, etc.) is specified in ``__path`` but invalid.

    Examples
    --------
    >>> neclib.core.files.read("relative/path/to/local-file.txt")
    >>> neclib.core.files.read("/absolute/path/to/local-file.txt")
    >>> neclib.core.files.read("https://example.com/file.txt")
    >>> neclib.core.files.read("http://192.168.xxx.xxx:80/file.txt")

    """
    if (not isinstance(__path, (str, os.PathLike))) and hasattr(__path, "read"):
        return __path.read()

    name = str(__path)
    _parsed = urlparse(name)
    scheme, path = _parsed.scheme, _parsed.path
    if scheme not in ("", "file"):
        if not allow_remote:
            raise FileNotFoundError(
                f"{name!r} appears to be a remote file, "
                "but remote access isn't allowed."
            )
        with urlopen(name) as response:
            return response.read().decode("utf-8")

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"{name!r} does not exist.")
    try:
        return path.read_text()
    except UnicodeDecodeError:
        return path.read_bytes().decode("utf-8")
