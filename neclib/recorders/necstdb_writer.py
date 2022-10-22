import queue
import time
import traceback
from pathlib import Path
from threading import Event, Thread
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union

import necstdb

from .. import get_logger
from ..typing import TextLike
from .writer_base import Writer

TextData = Union[TextLike, List[TextLike]]


def parse_str_size(data: TextData) -> Tuple[str, int]:
    length = len(data) if isinstance(data, TextLike) else max(map(len, data))
    return f"{length}s", 1 * length


def str_to_bytes(data: TextData) -> bytes:
    if isinstance(data, TextLike):
        return data if isinstance(data, bytes) else data.encode("utf-8")
    else:
        return [str_to_bytes(elem) for elem in data]


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

    def __init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__)

        self.db: Optional[necstdb.necstdb.necstdb] = None
        self.tables: Dict[str, necstdb.necstdb.table] = {}

        self.recording_path: Optional[Path] = None

        self._data_queue = queue.Queue()
        self._thread = None

        self._stop_event: Optional[Event] = None
        self._table_last_update: Dict[str, float] = {}

    def start_recording(self, record_dir: Path) -> None:
        self.recording_path = record_dir

        # Use root directory of current record as database.
        self.db = necstdb.opendb(record_dir, mode="w")

        self._stop_event = Event()
        self._thread = Thread(target=self._update_background, daemon=True)
        self._thread.start()

    def append(
        self, topic: str = None, chunk: List[Dict[str, Any]] = None, *args, **kwargs
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
        if not (
            isinstance(chunk, Iterable)
            and all([isinstance(field, dict) for field in chunk])
            and all([{"key", "type", "value"} <= field.keys() for field in chunk])
        ):  # This writer only handles data passes this condition.
            return False
        if self.db is None:
            self.logger.warning("Database is not opened. Data will be lost.")
            return False

        self._data_queue.put((topic, chunk))
        return True

    def stop_recording(self) -> None:
        self._stop_event.set()
        while self._stop_event is not None:
            # Wait until `_cleanup_thread` completes.
            time.sleep(0.1)

        self.db = None
        [table.close() for table in self.tables.values()]
        self.tables.clear()
        self._table_last_update.clear()
        self.recording_path = None

    def _update_background(self) -> None:
        while not self._stop_event.is_set():
            self._check_liveliness()
            if self._data_queue.empty():
                time.sleep(0.01)
                continue
            if self._data_queue.qsize() > self.WarningQueueSize:
                self.logger.warning("Too many data waiting for being dumped.")
            topic, chunk = self._data_queue.get()
            self._write(topic, chunk)

        if not self._data_queue.empty():
            qsize = self._data_queue.qsize()
            self.logger.info(f"Dumping received data: {qsize} remaining...")
        while not self._data_queue.empty():
            topic, chunk = self._data_queue.get()
            self._write(topic, chunk)
        self._cleanup_thread()
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

            for field in chunk:
                parsed = self._parse_field(field)
                if parsed is None:
                    return
                _data, _metadata = parsed
                data.extend(_data)
                metadata.append(_metadata)
            if topic not in self.tables:
                record_writer = self.__class__.__name__
                self.add_table(
                    topic,
                    {"data": metadata, "memo": f"Generated by {record_writer}"},
                )
            self.tables[topic].append(*data)
        except Exception:
            self.logger.error(traceback.format_exc())

    def _parse_field(self, field: Dict[str, Any]) -> Tuple[List[Any], Dict[str, str]]:
        data = None
        for k in self.DTypeConverters:
            if field["type"].find(k) != -1:
                data, fmt, size = self.DTypeConverters[k](field["value"])
                break
        if data is None:
            return
        if isinstance(data, Iterable) and (not isinstance(data, TextLike)):

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
        return data, {"key": field["key"], "format": fmt, "size": size}

    def _cleanup_thread(self) -> None:
        self._stop_event = None
        self._thread = None

    def _validate_name(self, topic: str) -> str:
        return topic.replace("/", "-").strip("-")

    def add_table(self, topic: str, metadata: Dict[str, Any]) -> None:
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
