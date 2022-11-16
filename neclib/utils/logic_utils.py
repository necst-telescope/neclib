"""Utility functions for real-time control logics."""

__all__ = ["busy"]

import time


class busy:
    """Manages the busy state of the object.

    This context manager blocks and stops the execution of its contents until the object
    confirmed to be not busy. When the context manager exits, it frees the busy flag.
    This functionality would be useful to avoid conflicting operations to be executed at
    the same time.

    Parameters
    ----------
    obj
        The object to manage the busy state of.
    flagname
        The name of the attribute to use to store the busy state.

    Examples
    --------
    >>> class Foo:
    ...     def task_a(self):
    ...         with busy(self, "busy"):
    ...             print("Task A")
    ...             time.sleep(1)
    ...             print("Task A done")
    ...     def task_b(self):
    ...         with busy(self, "busy"):
    ...             print("Task B")
    ...             time.sleep(0.5)
    ...             print("Task B done")
    >>> with concurrent.futures.ThreadPoolExecutor() as executor:
    ...     foo = Foo()
    ...     future1 = executor.submit(foo.task_a)
    ...     future2 = executor.submit(foo.task_b)
    ...     concurrent.futures.wait([future1, future2])

    The above example attempts to execute two tasks concurrently. However, the ``busy``
    context prevents the second task from starting until the first task finishes.

    Attention
    ---------
    The ``flagname`` argument must be the same across all ``busy`` contexts which blocks
    each other. To manage multiple busy states, use different ``flagname``-s to
    distinguish the task groups.

    """

    class __busyflag:
        def __init__(self, busy: bool = False):
            self.busy = busy

    def __init__(self, obj: object, flagname: str) -> None:
        if hasattr(obj, flagname) and (
            not isinstance(getattr(obj, flagname), self.__busyflag)
        ):
            raise ValueError(f"Object {obj!r} already has attribute {flagname!r}")
        self.__obj = obj
        self.__flagname = flagname

    @property
    def busy(self) -> bool:
        if not hasattr(self.__obj, self.__flagname):
            object.__setattr__(self.__obj, self.__flagname, self.__busyflag())
        return getattr(self.__obj, self.__flagname).busy

    @busy.setter
    def busy(self, value: bool) -> None:
        getattr(self.__obj, self.__flagname).busy = value

    def __enter__(self) -> None:
        while self.busy:
            time.sleep(0.05)
        self.busy = True

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.busy = False
        delattr(self.__obj, self.__flagname)
        if exc_type is not None:
            raise
