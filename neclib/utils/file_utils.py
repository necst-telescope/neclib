__all__ = ["read_file"]

import os
from pathlib import Path
from typing import Union, overload
from urllib.parse import urlparse
from urllib.request import urlopen


@overload
def read_file(
    name: str, /, saveto: None, overwrite: bool, localonly: bool
) -> Union[str, bytes]:
    ...


@overload
def read_file(
    name: str, /, saveto: os.PathLike, overwrite: bool, localonly: bool
) -> None:
    ...


def read_file(name, /, saveto=None, overwrite=False, localonly=False):
    name = str(name)
    if urlparse(name).scheme:
        if localonly and (urlparse(name).scheme != "file"):
            raise FileNotFoundError(f"{name} appears to be a remote file.")
        with urlopen(name) as response:
            contents = response.read().decode("utf-8")
    elif Path(name).exists():
        path = Path(name)
        try:
            contents = path.read_text()
        except UnicodeDecodeError:
            contents = path.read_bytes()
    else:
        raise FileNotFoundError(f"Cannot find {name!r}.")

    if saveto is not None:
        save_path = Path(saveto)
        if save_path.exists() and not overwrite:
            raise FileExistsError(f"{save_path} already exists.")

        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.touch(exist_ok=True)
        try:
            save_path.write_text(contents)
        except TypeError:
            save_path.write_bytes(contents)
        return
    return contents
