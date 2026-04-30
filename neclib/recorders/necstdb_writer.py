import queue
import time
import traceback
from pathlib import Path
from threading import Event, Thread
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union

import necstdb

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

    WarningIntervalSec: float = 5.0
    """Minimum interval between repeated backlog warnings."""

    HealthyLogIntervalSec: float = 15.0
    """Minimum interval between repeated healthy queue status logs."""

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
        if not self._initialized[self.__class__]:
            self.logger = get_logger(self.__class__.__name__)

            self.db: Optional[necstdb.necstdb.necstdb] = None
            self.tables: Dict[str, necstdb.necstdb.table] = {}

            self.recording_path: Optional[Path] = None

            self._data_queue = queue.Queue()
            self._thread = None

            self._stop_event: Optional[Event] = None
            self._table_last_update: Dict[str, float] = {}

            self._peak_qsize: int = 0
            self._last_warn_time: float = 0.0
            self._last_healthy_log_time: float = 0.0
            self._backlog_warned: bool = False

            self._initialized[self.__class__] = True

    def start_recording(self, record_dir: Path) -> None:
        self.recording_path = record_dir

        # Use root directory of current record as database.
        self.db = necstdb.opendb(record_dir, mode="w")

        self._peak_qsize = 0
        self._last_warn_time = 0.0
        self._last_healthy_log_time = time.time()
        self._backlog_warned = False

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
        if not (
            isinstance(chunk, Iterable)
            and all([isinstance(field, dict) for field in chunk])
            and all([{"key", "type", "value"} <= field.keys() for field in chunk])
        ):  # This writer only handles data passes this condition.
            return False
        if self.db is None:
            self.logger.warning("Database is not opened. Data will be lost.")
            return False

        self._data_queue.put((time.time(), topic, chunk))
        qsize = self._data_queue.qsize()
        if qsize > self._peak_qsize:
            self._peak_qsize = qsize
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

    def _update_background(self) -> None:
        while (self._stop_event is not None) and (not self._stop_event.is_set()):
            self._check_liveliness()
            self._maybe_log_queue_backlog()

            if self._data_queue.empty():
                time.sleep(0.01)
                continue

            _enqueue_time, topic, chunk = self._data_queue.get()
            self._write(topic, chunk)

        qsize, oldest_wait_sec = self._get_queue_diagnostics()
        if qsize > 0:
            self.logger.info(
                "Dumping received data: "
                f"qsize={qsize}, peak_qsize={self._peak_qsize}, "
                f"oldest_wait_sec={oldest_wait_sec:.1f}"
            )

        while not self._data_queue.empty():
            _enqueue_time, topic, chunk = self._data_queue.get()
            self._write(topic, chunk)

        self.logger.info("NECSTDB has gracefully been stopped.")

    def _get_queue_diagnostics(self) -> Tuple[int, float]:
        now = time.time()
        with self._data_queue.mutex:
            qsize = len(self._data_queue.queue)
            if qsize == 0:
                return 0, 0.0
            oldest_enqueue_time = self._data_queue.queue[0][0]
        oldest_wait_sec = max(0.0, now - oldest_enqueue_time)
        return qsize, oldest_wait_sec

    def _maybe_log_queue_backlog(self) -> None:
        qsize, oldest_wait_sec = self._get_queue_diagnostics()
        if qsize > self._peak_qsize:
            self._peak_qsize = qsize

        now = time.time()

        if qsize > self.WarningQueueSize:
            if (not self._backlog_warned) or (
                now - self._last_warn_time >= self.WarningIntervalSec
            ):
                self.logger.warning(
                    "Too many data waiting for being dumped: "
                    f"qsize={qsize}, peak_qsize={self._peak_qsize}, "
                    f"oldest_wait_sec={oldest_wait_sec:.1f}"
                )
                self._last_warn_time = now
                self._backlog_warned = True
        else:
            if self._backlog_warned:
                self.logger.info(
                    "Queue backlog recovered: "
                    f"qsize={qsize}, peak_qsize={self._peak_qsize}, "
                    f"oldest_wait_sec={oldest_wait_sec:.1f}"
                )
                self._backlog_warned = False
                self._last_healthy_log_time = now
            elif now - self._last_healthy_log_time >= self.HealthyLogIntervalSec:
                self.logger.info(
                    "Queue status: "
                    f"qsize={qsize}, peak_qsize={self._peak_qsize}, "
                    f"oldest_wait_sec={oldest_wait_sec:.1f}"
                )
                self._last_healthy_log_time = now

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
            chunk = str(chunk)
            chunk = chunk[: min(100, len(chunk))]
            self.logger.error(f"{traceback.format_exc()}\ndata={chunk} ({topic=})")

    def _parse_field(
        self, field: Dict[str, Any]
    ) -> Optional[Tuple[List[Any], Dict[str, str]]]:
        data = fmt = size = None
        for k in self.DTypeConverters:
            if field["type"].find(k) != -1:
                data, fmt, size = self.DTypeConverters[k](field["value"])
                break
        if (data is None) or (fmt is None) or (size is None):
            return

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
        return data, {"key": field["key"], "format": fmt, "size": size}

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
