"""Inform deprecation."""

import warnings
from functools import wraps
from typing import Any, Callable, Optional


def _deprecation_message(
    name: str,
    /,
    version_since: Optional[str] = None,
    version_removed: Optional[str] = None,
    reason: Optional[str] = None,
    replacement: Optional[str] = None,
) -> str:
    message = f"The use of `{name}` is deprecated"
    if version_since:
        message += f" since version {version_since}"
    if version_removed:
        message += f" and will be removed in version {version_removed}"
    message += "."
    if reason:
        message += f" The reason for deprecation is {reason}."
    if replacement:
        message += f" Use `{replacement}` instead."
    else:
        message += " There is no replacement."
    return message


def deprecated(
    __callable: Optional[Callable[..., Any]] = None,
    *,
    version_since: Optional[str] = None,
    version_removed: Optional[str] = None,
    reason: Optional[str] = None,
    replacement: Optional[str] = None,
) -> Callable[..., Any]:
    """Decorator to mark a function as deprecated.

    Parameters
    ----------
    __callable
        A callable object to be decorated.
    version_since
        The version since which the function is deprecated.
    version_removed
        The version in which the function will be removed.
    reason
        The reason for deprecation.
    replacement
        The replacement for the deprecated function.

    Returns
    -------
    deprecated
        A callable object with deprecation warning.

    Examples
    --------
    >>> @deprecated
    ... def foo():
    ...     pass
    >>> foo()
    DeprecationWarning: The use of `foo` is deprecated. There is no replacement.

    """

    def wrapper(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            message = _deprecation_message(
                func.__name__,
                version_since=version_since,
                version_removed=version_removed,
                reason=reason,
                replacement=replacement,
            )
            warnings.warn(message, category=DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        return wrapped

    if __callable is None:
        return wrapper
    else:
        return wrapper(__callable)


class deprecated_namespace:
    """Deprecated namespace.

    Parameters
    ----------
    __namespace
        The namespace to be deprecated.
    __deprecated_path
        The path of the deprecated namespace.
    version_since
        The version since which the namespace is deprecated.
    version_removed
        The version in which the namespace will be removed.
    reason
        The reason for deprecation.
    replacement
        The replacement for the deprecated namespace.

    Examples
    --------
    >>> from neclib.core import deprecated_namespace
    >>> from neclib.core import exceptions as core_exceptions
    >>> exceptions = deprecated_namespace(
    ...     core_exceptions,
    ...     "neclib.exceptions",
    ...     version_since="0.22.0",
    ...     version_removed="1.0.0",
    ...     replacement="neclib.core.exceptions",
    ... )
    >>> exceptions.NECSTAuthorityError
    DeprecationWarning: The use of `neclib.exceptions` is deprecated since version
    0.22.0 and will be removed in version 1.0.0. Use `neclib.core.exceptions` instead.
    <class 'neclib.core.exceptions.NECSTAuthorityError'>

    """

    def __init__(
        self,
        __namespace: Any,
        __deprecated_path: str,
        /,
        version_since: Optional[str] = None,
        version_removed: Optional[str] = None,
        reason: Optional[str] = None,
        replacement: Optional[str] = None,
    ) -> None:
        self.__vars = vars(__namespace)
        self.__msg = _deprecation_message(
            __deprecated_path,
            version_since=version_since,
            version_removed=version_removed,
            reason=reason,
            replacement=replacement or __namespace.__name__,
        )

    def __getattr__(self, key: str) -> Any:
        if key in self.__vars:
            warnings.warn(self.__msg, category=DeprecationWarning, stacklevel=2)
            return self.__vars[key]
