import time
from typing import Any, Callable, Generic, Optional, Type, TypeVar

from ..formatting import html_repr_of_status

T = TypeVar("T", bound=Type)


class StatusManager(Generic[T]):
    """Manage multiple contexts.

    Parameters
    ----------
    ctx_type
        A dataclass type which keeps single status/context. The arguments of its
        constructor should have default values, otherwise ``get(out_of_range)`` will
        fail.
    start
        Name of the attribute which stores the start index of the context. The index
        would typically be the time.
    stop
        Name of the attribute which stores the stop index of the context.
    idx_getter
        A function which returns the current index. This function is called with no
        arguments.
    keep
        Maximum index difference from current one to keep the context. Contexts with
        index difference larger than this value will be removed.

    Examples
    --------
    >>> @dataclass
    ... class Context:
    ...     start: Optional[float] = None
    ...     stop: Optional[float] = None
    ...     value: int = 0
    >>> manager = StatusManager(Context)
    >>> manager.get(time.time())
    Context(start=None, stop=None, value=0)  # default value
    >>> manager.set(start=time.time(), stop=time.time() + 10, value=100)
    >>> manager.get(time.time())
    Context(start=..., stop=..., value=100)

    """

    def __init__(
        self,
        ctx_type: Type[T],
        /,
        start: str = "start",
        stop: str = "stop",
        idx_getter: Callable[[], float] = time.time,
        keep: float = 60,
    ) -> None:
        self.ctx = []
        self.start = start
        self.stop = stop
        self.ctx_type = ctx_type
        self.idx_getter = idx_getter
        self.keep = keep

    def _sort(self) -> None:
        self.ctx.sort(key=lambda x: getattr(x, self.start))

        # Remove stale contexts.
        current_idx = self.idx_getter()
        threshold = current_idx - self.keep
        outdated = [ctx for ctx in self.ctx if getattr(ctx, self.stop) < threshold]
        [self.ctx.remove(ctx) for ctx in outdated]

    def get(self, idx: float, /) -> T:
        """Find the context that contains the specified index value.

        Parameters
        ----------
        idx : float
            The index value to search for.

        Returns
        -------
        The context that contains the specified index value.

        """
        not_future = [ctx for ctx in self.ctx if getattr(ctx, self.start) <= idx]
        for ctx in reversed(not_future):
            # This search is done from the end of the context list so that the newer
            # context takes precedence. Caution this is not the context setting order.
            if (getattr(ctx, self.stop) is None) or (idx < getattr(ctx, self.stop)):
                return ctx

        # If no context is found, return the default values.
        return self.ctx_type()

    def set(self, _obj: Optional[T] = None, /, **kwargs: Any) -> None:
        """Set the context.

        Parameters
        ----------
        kwargs
            Keyword arguments to be passed to the constructor of the context type.

        """
        if _obj is not None:
            self.ctx.append(_obj)
        else:
            ctx = self.ctx_type(**kwargs)
            self.ctx.append(ctx)
        self._sort()

    def _repr_html_(self) -> str:
        return html_repr_of_status(self)
