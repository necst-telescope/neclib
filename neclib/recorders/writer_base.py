from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class Writer(ABC):
    @abstractmethod
    def start_recording(self, record_dir: Path) -> None:
        ...

    @abstractmethod
    def append(self, *args: Any, **kwargs: Any) -> bool:
        """Append a chunk of data.

        Returns
        -------
        handled
            Whether the data is handled by this writer.

        Notes
        -----
        The subclass should check the input type, as ``Writer`` would handle some
        essentially different data, and ``Recorder`` won't implement the type checking
        for extensibility.

        """
        ...

    @abstractmethod
    def stop_recording(self) -> None:
        ...
