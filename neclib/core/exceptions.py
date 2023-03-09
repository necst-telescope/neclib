"""Informative exception, regarding the NECST system status."""

__all__ = [
    "NECSTAuthorityError",
    "NECSTConfigurationError",
    "NECSTTimeoutError",
    "NECSTAccessibilityWarning",
    "NECSTParameterNameError",
]


class NECSTAuthorityError(PermissionError):
    """Error related to controlling priority.

    Examples
    --------
    >>> raise neclib.NECSTAuthorityError("reason or advise to fix this error")

    """

    pass


class NECSTConfigurationError(Exception):
    """Error related to parameter configuration."""

    pass


class NECSTTimeoutError(TimeoutError):
    """Error related to communication timeout."""

    pass


class NECSTParameterNameError(AttributeError):
    """Error related to limitation on parameter name."""

    pass


class NECSTAccessibilityWarning(UserWarning):
    """Warning on limited usage."""

    pass


class NotInitializedError(TypeError):
    """Error related to object initialization status."""

    pass
