__all__ = ["read_file"]

import os
from pathlib import Path
from typing import Union, overload
from urllib.parse import urlparse
from urllib.request import urlopen


@overload
def read_file(name: str, /, saveto: None = None) -> Union[str, bytes]:
    ...


@overload
def read_file(name: str, /, saveto: os.PathLike) -> None:
    ...


def read_file(name, /, saveto=None):
    name = str(name)
    if urlparse(name).scheme:
        with urlopen(name) as response:
            contents = response.read().decode("utf-8")
    elif Path(name).exists():
        path = Path(name)
        try:
            contents = path.read_text()
        except UnicodeDecodeError:
            contents = path.read_bytes()
    else:
        raise ValueError(f"Cannot find {name!r}.")

    if saveto is not None:
        save_path = Path(saveto)
        try:
            save_path.write_text(contents)
        except TypeError:
            save_path.write_bytes(contents)
        return
    return contents
