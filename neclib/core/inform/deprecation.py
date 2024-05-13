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


def deprecated_namespace(*args, **kwargs):
    raise NotImplementedError
