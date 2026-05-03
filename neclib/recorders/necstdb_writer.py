import queue
import struct
import time
import traceback
from pathlib import Path
from threading import Event, Thread
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union

import necstdb

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None

from ..core import get_logger
from ..core.types import TextLike
from .writer_base import Writer

TextData = Union[TextLike, List[TextLike]]


def parse_str_size(data: TextData) -> Tuple[str, int]:
    length = len(data) if isinstance(data, TextLike) else max(map(len, data))
    return f"{length}s", 1 * length


def str_to_bytes(data: TextData) -> Union[bytes, List[bytes]]:
    if isinstance(data, TextLike):
        return data if isinstance(data, bytes) else data.encode("utf-8")  # type: ignore
    else:
        return [str_to_bytes(elem) for elem in data]  # type: ignore


class NECSTDBWriter(Writer):
    """Dump data to NECSTDB.

    Attributes
    ----------
    db : necstdb.necstdb.necstdb or None
        Database instance this writer is currently dumping data to.
    tables : Dict[str, necstdb.necstdb.table]
        NECSTDB Table to which this writer is dumping data.

    Examples
    --------
    >>> writer = neclib.recorders.NECSTDBWriter()
    >>> writer.start_recording("path/to/database/directory.necstdb")
    >>> chunk = [
    ...     {"key": "timestamp", "type": "double", "value": 1664195057.022712},
    ...     {"key": "pressure", "type": "float32", "value": 850.5},
    ... ]
    >>> writer.append("/observatory/pressure", chunk)
    >>> writer.stop_recording()

    """

    LivelinessDuration: float = 15.0
    """If a table isn't updated for this duration (in sec), it will be closed."""

    WarningQueueSize: int = 1000
    """Warn if number of data waiting for being dumped is greater than this."""

    DrainBurstSize: int = 64
    """Maximum number of queued chunks to write before checking control state."""

    LivelinessCheckInterval: float = 1.0
    """Minimum interval in seconds between table liveliness scans."""

    DTypeConverters: Dict[str, Callable[[Any], Tuple[Any, str, int]]] = {
        "bool": lambda dat: (dat, "?", 1),
        "byte": lambda dat: (dat, *parse_str_size(dat)),
        "char": lambda dat: (dat, "c", 1),
        "float32": lambda dat: (dat, "f", 4),
        "float": lambda dat: (dat, "f", 4),
        "float64": lambda dat: (dat, "d", 8),
        "double": lambda dat: (dat, "d", 8),
        "int8": lambda dat: (dat, "b", 1),
        "int16": lambda dat: (dat, "h", 2),
        "int32": lambda dat: (dat, "i", 4),
        "int64": lambda dat: (dat, "q", 8),
        "uint8": lambda dat: (dat, "B", 1),
        "uint16": lambda dat: (dat, "H", 2),
        "uint32": lambda dat: (dat, "I", 4),
        "uint64": lambda dat: (dat, "Q", 8),
        "string": lambda dat: (str_to_bytes(dat), *parse_str_size(dat)),
    }
    """Converter from readable type name to C data structure."""

    _NumpyDTypeByFormat: Dict[str, str] = {
        "?": "?",
        "b": "i1",
        "B": "u1",
        "h": "<i2",
        "H": "<u2",
        "i": "<i4",
        "I": "<u4",
        "q": "<i8",
        "Q": "<u8",
        "f": "<f4",
        "d": "<f8",
    }

    def __init__(self) -> None:
        if not self._initialized[self.__class__]:
            self.logger = get_logger(self.__class__.__name__)

            self.db: Optional[necstdb.necstdb.necstdb] = None
            self.tables: Dict[str, necstdb.necstdb.table] = {}

            self.recording_path: Optional[Path] = None

            self._data_queue = queue.Queue()
            self._thread = None

            self._stop_event: Optional[Event] = None
            self._table_last_update: Dict[str, float] = {}
            self._last_liveliness_check = 0.0

            self._initialized[self.__class__] = True

    def start_recording(self, record_dir: Path) -> None:
        self.recording_path = record_dir

        # Use root directory of current record as database.
        self.db = necstdb.opendb(record_dir, mode="w")

        self._stop_event = Event()
        self._thread = Thread(target=self._update_background, daemon=True)
        self._thread.start()

    def append(
        self,
        topic: Optional[str] = None,
        chunk: Optional[List[Dict[str, Any]]] = None,
        *args,
        **kwargs,
    ) -> bool:
        """Append a chunk of data.

        Returns
        -------
        handled
            Whether the data is handled by this writer.

        Examples
        --------
        >>> chunk = [
                {"key": "timestamp", "type": "double", "value": 1664195057.022712},
                {"key": "reading", "type": "int32", "value": 5},
            ]
        >>> writer.append("/meter_reading", chunk)

        """
        if not isinstance(chunk, Iterable):
            return False
        for field in chunk:
            if not (
                isinstance(field, dict)
                and ("key" in field)
                and ("type" in field)
                and ("value" in field)
            ):  # This writer only handles data that passes this condition.
                return False
        if self.db is None:
            self.logger.warning("Database is not opened. Data will be lost.")
            return False

        self._data_queue.put((topic, chunk))
        return True

    def stop_recording(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()
        if self._thread is not None:
            self._thread.join()

        self._stop_event = self._thread = None

        self.db = None
        [table.close() for table in self.tables.values()]
        self.tables.clear()
        self._table_last_update.clear()
        self.recording_path = None

    def _maybe_check_liveliness(self) -> None:
        now = time.time()
        if now - self._last_liveliness_check >= self.LivelinessCheckInterval:
            self._last_liveliness_check = now
            self._check_liveliness()

    def _drain_once(self, *, wait: bool = False) -> bool:
        try:
            if wait:
                topic, chunk = self._data_queue.get(timeout=0.01)
            else:
                topic, chunk = self._data_queue.get_nowait()
        except queue.Empty:
            return False
        self._write(topic, chunk)
        return True

    def _drain_burst(self, *, wait_first: bool = False) -> int:
        drained = 0
        if not self._drain_once(wait=wait_first):
            return drained
        drained += 1
        for _ in range(self.DrainBurstSize - 1):
            if not self._drain_once(wait=False):
                break
            drained += 1
        return drained

    def _warn_if_queue_is_large(self) -> None:
        if self._data_queue.qsize() > self.WarningQueueSize:
            self.logger.warning("Too many data waiting for being dumped.")

    def _update_background(self) -> None:
        while (self._stop_event is not None) and (not self._stop_event.is_set()):
            self._maybe_check_liveliness()
            drained = self._drain_burst(wait_first=True)
            if drained:
                self._warn_if_queue_is_large()

        if not self._data_queue.empty():
            qsize = self._data_queue.qsize()
            self.logger.info(f"Dumping received data: {qsize} remaining...")
        while self._drain_burst(wait_first=False):
            pass
        self.logger.info("NECSTDB has gracefully been stopped.")

    def _check_liveliness(self) -> None:
        table_names = list(self.tables.keys())
        # Conversion to list is workaround for deepcopy (cannot deepcopy keys obj)
        # Object copying avoids dict size change during iteration in the following lines

        now = time.time()
        for topic in table_names:
            if now - self._table_last_update[topic] > self.LivelinessDuration:
                self.remove_table(topic)

    def _write(self, topic: str, chunk: List[Dict[str, Any]]) -> None:
        try:
            now = time.time()
            self._table_last_update[topic] = now

            data = [now]
            metadata = [{"key": "recorded_time", "format": "d", "size": 8}]
            record_parts = [struct.pack("<d", now)]
            can_pack_direct = True

            for field in chunk:
                parsed = self._parse_field(field)
                if parsed is None:
                    return
                _data, _metadata, _raw_bytes = parsed
                metadata.append(_metadata)
                if _raw_bytes is not None:
                    record_parts.append(_raw_bytes)
                else:
                    fmt = "<" + str(_metadata["format"])
                    record_parts.append(struct.pack(fmt, *_data))
                    data.extend(_data)

            if topic not in self.tables:
                record_writer = self.__class__.__name__
                self.add_table(
                    topic,
                    {"data": metadata, "memo": f"Generated by {record_writer}"},
                )

            if can_pack_direct and hasattr(self.tables[topic], "append_packed"):
                record = b"".join(record_parts)
                self.tables[topic].append_packed(record)
            else:
                # Compatibility fallback for older necstdb without append_packed.
                # If raw array bytes were used, expand them only in this fallback path.
                data = [now]
                for field in chunk:
                    parsed = self._parse_field(field)
                    if parsed is None:
                        return
                    _data, _metadata, _raw_bytes = parsed
                    if _raw_bytes is None:
                        data.extend(_data)
                    else:
                        fmt = "<" + str(_metadata["format"])
                        data.extend(struct.unpack(fmt, _raw_bytes))
                self.tables[topic].append(*data)
        except Exception:
            chunk = str(chunk)
            chunk = chunk[: min(100, len(chunk))]
            self.logger.error(f"{traceback.format_exc()}\\ndata={chunk} ({topic=})")

    def _numpy_array_to_raw_field(
        self,
        data: Any,
        fmt: str,
        elem_size: int,
    ) -> Optional[Tuple[List[Any], str, int, bytes]]:
        if np is None or not isinstance(data, np.ndarray):
            return None
        if fmt not in self._NumpyDTypeByFormat:
            return None
        arr = np.asarray(data)
        if arr.ndim != 1:
            arr = arr.reshape(-1)
        dtype = np.dtype(self._NumpyDTypeByFormat[fmt])
        arr = np.ascontiguousarray(arr.astype(dtype, copy=False))
        length = int(arr.size)
        raw = arr.tobytes(order="C")
        return [], f"{length}{fmt}", elem_size * length, raw

    def _parse_field(
        self, field: Dict[str, Any]
    ) -> Optional[Tuple[List[Any], Dict[str, str], Optional[bytes]]]:
        data = fmt = size = None
        type_name = str(field["type"])
        converter = self.DTypeConverters.get(type_name)
        if converter is None and type_name.startswith("string<="):
            # Backward-compatible annotation accepted as variable-length string.
            # Callers that require fixed-length NECSTDB columns must still pass a
            # bytes value already padded to the desired length, because the writer
            # derives the actual ``Ns`` struct format from the value length.
            converter = self.DTypeConverters["string"]
        if converter is None:
            self.logger.warning(f"Unsupported NECSTDB field type: {type_name!r}")
            return
        data, fmt, size = converter(field["value"])
        if (data is None) or (fmt is None) or (size is None):
            return

        raw_array = self._numpy_array_to_raw_field(data, fmt, size)
        if raw_array is not None:
            _data, fmt, size, raw_bytes = raw_array
            return _data, {"key": field["key"], "format": fmt, "size": size}, raw_bytes

        if isinstance(data, Sequence) and (not isinstance(data, TextLike)):
            length = len(data)
            if fmt.find("s") != -1:
                fmt = "0s" if length == 0 else fmt * length
                # Because 5s5s5s is ok, but 35s has different meaning.
            else:
                fmt = f"{length}{fmt}"
            size *= length
            data = list(data)
        else:
            data = [data]
        return data, {"key": field["key"], "format": fmt, "size": size}, None

    def _validate_name(self, topic: str) -> str:
        return topic.replace("/", "-").strip("-")

    def add_table(self, topic: str, metadata: Dict[str, Any]) -> None:
        if self.db is None:
            raise RuntimeError("Database is not opened.")

        _topic = self._validate_name(topic)
        if topic in self.tables:
            self.logger.warning(f"Table {topic} already opened.")
            return
        if _topic not in self.db.list_tables():
            metadata.update({"necstdb_version": necstdb.__version__})
            self.db.create_table(_topic, metadata)
        self.tables[topic] = self.db.open_table(_topic, mode="ab")
        self._table_last_update[topic] = time.time()

    def remove_table(self, topic: str) -> None:
        if topic in self.tables:
            self.tables[topic].close()
        self.tables.pop(topic, None)
        self._table_last_update.pop(topic, None)
