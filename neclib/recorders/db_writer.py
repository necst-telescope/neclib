__all__ = ["DBWriter"]

import logging
import queue
import time
import traceback
from datetime import datetime
from pathlib import Path
from threading import Event, Thread
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

import necstdb

from ..typing import PathLike


def str_to_bytes(data: Union[str, bytes, List[Union[str, bytes]]]) -> bytes:
    try:
        return data if isinstance(data, bytes) else data.encode("utf-8")
    except AttributeError:
        return [str_to_bytes(elem) for elem in data]


def parse_str_size(data: Union[str, bytes, List[Union[str, bytes]]]) -> Tuple[str, int]:
    length = len(data) if isinstance(data, (str, bytes)) else max(map(len, data))
    return f"{length}s", 1 * length


class DBWriter:
    """Dump data to NECSTDB.

    Parameters
    ----------
    record_root
        Root directory of data storage. All the data will be stored inside a structured
        directory tree, but they are created under this single directory.

    Attributes
    ----------
    db : necstdb.necstdb.necstdb or None
        Database instance to which this writer is currently dumping data.
    tables : Dict[str, necstdb.necstdb.table]
        NECSTDB Table to which this writer is dumping data.

    Examples
    --------
    >>> writer = neclib.recorders.DBWriter("/home/user/data")

    """

    LivelinessDuration: float = 15.0
    """If a table isn't updated in this duration (in sec), it'll be closed."""

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

    def __init__(self, record_root: PathLike) -> None:
        self.logger = logging.getLogger(__name__)

        self.record_root = Path(record_root)

        self.db: Optional[necstdb.necstdb.necstdb] = None
        self.tables: Dict[str, necstdb.necstdb.table] = {}

        self._data_queue = queue.Queue()
        self._thread = None

        self._stop_event: Optional[Event] = None
        self.recording = False
        self._db_name: Optional[str] = None
        self._table_last_update: Dict[str, float] = {}

    def start_recording(self, name: str = None) -> Path:
        self.recording = True
        self._db_name = name
        db_path = self.record_root / (name or self._get_date_str())
        self.db = necstdb.opendb(db_path, mode="w")

        self._stop_event = Event()
        self._thread = Thread(target=self._update_background, daemon=True)
        self._thread.start()

        return db_path

    def append(self, name: str, data: List[Dict[str, Any]]) -> None:
        """Append a chunk of data.

        Examples
        --------
        >>> chunk = [
                {"key": "timestamp", "type": "double", "value": 1664195057.022712},
                {"key": "reading", "type": "int32", "value": 5},
            ]
        >>> writer.append("/meter_reading", chunk)

        """
        if self.recording:
            self._data_queue.put([name, data])
            return
        self.logger.warning("Recorder not started. Incoming data won't be kept.")

    def stop_recording(self) -> Path:
        self.recording = False
        self._db_name = None
        self._stop_event.set()

        while self._stop_event:  # `cleanup` not completed
            time.sleep(0.01)

    def _update_background(self) -> None:
        while not self._stop_event.is_set():
            self._check_date()
            self._check_liveliness()
            if self._data_queue.empty():
                time.sleep(0.01)
                continue
            name, data = self._data_queue.get()
            self._write(name, data)
        self.logger.info("Stopping data recorder...")
        if not self._data_queue.empty():
            qsize = self._data_queue.qsize()
            self.logger.info(f"Dumping received data: {qsize} remaining")
        while not self._data_queue.empty():
            # Dump data after stop_recording
            name, data = self._data_queue.get()
            try:
                self._write(name, data)
            except Exception:
                self.logger.error(traceback.format_exc())
        self._cleanup()

    def _cleanup(self):
        [table.close() for table in self.tables.values()]
        self.tables.clear()
        self._table_last_update.clear()

        self._stop_event = None
        self._thread = None
        self._db_name = None

    def _get_date_str(self) -> str:
        return datetime.utcnow().strftime("%Y%m/%Y%m%d.necstdb")

    def _write(self, name: str, data: List[Dict[str, Any]]) -> None:
        name = self._validate_name(name)
        now = time.time()
        self._table_last_update[name] = now

        table_data = [now]
        table_info = [{"key": "received_time", "format": "d", "size": 8}]
        for dat in data:
            _data, info = self._parse_slot(dat)
            table_data.extend(_data)
            table_info.append(info)
        if name not in self.tables:
            self.add_table(
                name,
                {"data": table_info, "memo": f"Generated by {self.__class__.__name__}"},
            )
        self.tables[name].append(*table_data)

    def _parse_slot(self, data: Dict[str, Any]) -> Tuple[List[Any], Dict[str, str]]:
        for k in self.DTypeConverters.keys():
            if data["type"].find(k) != -1:
                dat, format_, size = self.DTypeConverters[k](data["value"])
                break
        if isinstance(dat, Sequence) and (not isinstance(dat, (str, bytes))):
            length = len(dat)
            if format_.find("s") != -1:
                format_ = "0s" if length == 0 else format_ * length
                # Because 5s5s5s is ok, but 35s has different meaning.
            else:
                format_ = f"{length}{format_}"
            size *= length
            dat = list(dat)
        else:
            dat = [dat]
        return dat, {"key": data["key"], "format": format_, "size": size}

    def _check_date(self) -> None:
        if (self._db_name is None) and (self.db.path.name not in self._get_date_str()):
            self.stop_recording()
            self.start_recording()

    def _check_liveliness(self) -> None:
        table_names = list(self.tables.keys())
        # Conversion to list is workaround for deepcopy (cannot deepcopy keys obj)
        # Object copying avoids dict size change during iteration in the following lines

        now = time.time()
        for name in table_names:
            if now - self._table_last_update[name] > self.LivelinessDuration:
                self.remove_table(name)

    def _validate_name(self, name: str) -> str:
        return name.replace("/", "-").strip("-")

    def add_table(self, name: str, header: Dict[str, Any]) -> None:
        name = self._validate_name(name)
        if name in self.tables:
            self.logger.warning(f"Table '{name}' already opened.")
            return
        if name not in self.db.list_tables():
            header.update({"necstdb_version": necstdb.__version__})
            self.db.create_table(name, header)
        self.tables[name] = self.db.open_table(name, mode="ab")
        self._table_last_update[name] = time.time()

    def remove_table(self, name: str) -> None:
        name = self._validate_name(name)
        if name in self.tables:
            self.tables[name].close()
        self.tables.pop(name, None)
        self._table_last_update.pop(name, None)
