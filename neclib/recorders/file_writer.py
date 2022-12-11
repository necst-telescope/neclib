import time
from pathlib import Path
from typing import Optional

from .. import get_logger
from ..typing import TextLike
from .writer_base import Writer


class FileWriter(Writer):
    def __init__(self) -> None:
        if not self._initialized[self.__class__]:
            self.logger = get_logger(self.__class__.__name__)
            self.record_dir: Optional[Path] = None
            self._initialized[self.__class__] = True

    def start_recording(self, record_dir: Path) -> None:
        self.record_dir = record_dir

    def append(self, path: str, contents: TextLike, *args, **kwargs) -> bool:
        if not (isinstance(path, str) and isinstance(contents, TextLike)):
            return False
        if self.record_dir is None:
            self.logger.warning("FileWriter is not recording")
            return False

        header = f"# Original file: {path}\n# Recorded time: {time.time()}\n"

        write_path = self._find_new_path(path)
        write_path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(contents, bytes):
            write_path.write_bytes(header.encode("utf-8") + contents)
        else:
            write_path.write_text(header + contents)  # type: ignore

        return True

    def stop_recording(self) -> None:
        self.record_dir = None

    def _find_new_path(self, path: str, i: int = 0) -> Path:
        if self.record_dir is None:
            raise RuntimeError("FileWriter is not recording")

        _path = Path(path.split(":")[-1])
        _path = _path if i == 0 else _path.parent / f"{_path.stem}({i}){_path.suffix}"
        _path: Path = self.record_dir / _path.name
        return self._find_new_path(path, i + 1) if _path.exists() else _path
