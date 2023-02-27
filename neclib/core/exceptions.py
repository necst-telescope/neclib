"""Informative exception, regarding the NECST system status."""

__all__ = [
    "NECSTAuthorityError",
    "NECSTConfigurationError",
    "NECSTTimeoutError",
    "NECSTAccessibilityWarning",
    "NECSTParameterNameError",
]

pkg_name = "neclib"


class NECSTAuthorityError(PermissionError):
    """Error related to controlling priority.

    Examples
    --------
    >>> raise neclib.NECSTAuthorityError("reason or advise to fix this error")

    """

    __module__ = pkg_name


class NECSTConfigurationError(Exception):
    """Error related to parameter configuration."""

    __module__ = pkg_name


class NECSTTimeoutError(TimeoutError):
    """Error related to communication timeout."""

    __module__ = pkg_name


class NECSTParameterNameError(AttributeError):
    """Error related to limitation on parameter name."""

    __module__ = pkg_name


class NECSTAccessibilityWarning(UserWarning):
    """Warning on limited usage."""

    __module__ = pkg_name


class NotInitializedError(TypeError):
    """Error related to object initialization status."""

    __module__ = pkg_name
