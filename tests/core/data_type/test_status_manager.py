import time
from dataclasses import dataclass
from typing import Optional

from neclib.core import StatusManager


@dataclass
class Context:
    start: Optional[float] = None
    stop: Optional[float] = None
    value: int = 1


@dataclass
class CustomContext:
    initial: Optional[float] = None
    last: Optional[float] = None
    value: int = 1


class TestStatusManager:
    def test_get_context(self) -> None:
        manager = StatusManager(Context)
        now = time.time()
        manager.set(start=now, stop=now + 1, value=100)
        assert manager.get(now + 0.5) == Context(start=now, stop=now + 1, value=100)

    def test_set_obj(self) -> None:
        manager = StatusManager(Context)
        now = time.time()
        manager.set(Context(start=now, stop=now + 1, value=100))
        assert manager.get(now + 0.5) == Context(start=now, stop=now + 1, value=100)

    def test_get_out_of_range(self) -> None:
        manager = StatusManager(Context)
        now = time.time()
        manager.set(Context(start=now, stop=now + 1, value=100))
        default = Context()
        assert manager.get(now + 1.5) == default
        assert manager.get(now - 0.5) == default

    def test_get_empty(self) -> None:
        manager = StatusManager(Context)
        now = time.time()
        default = Context()
        assert manager.get(now) == default

    def test_override(self) -> None:
        manager = StatusManager(Context)
        now = time.time()
        manager.set(Context(start=now, stop=now + 2, value=100))
        manager.set(Context(start=now + 1, stop=now + 2, value=200))
        assert manager.get(now + 1.5) == Context(start=now + 1, stop=now + 2, value=200)

    def test_attr_name_for_start_and_stop(self) -> None:
        manager = StatusManager(CustomContext, start="initial", stop="last")
        now = time.time()
        manager.set(CustomContext(initial=now, last=now + 1, value=100))
        assert manager.get(now + 0.5) == CustomContext(
            initial=now, last=now + 1, value=100
        )

    def test_change_idx_getter(self) -> None:
        manager = StatusManager(Context, idx_getter=time.monotonic)
        now = time.monotonic()
        manager.set(Context(start=now, stop=now + 1, value=100))
        assert manager.get(now + 0.5) == Context(start=now, stop=now + 1, value=100)
