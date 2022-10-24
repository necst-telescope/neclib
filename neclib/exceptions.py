"""Informative exception, regarding the NECST system status."""

__all__ = ["NECSTAuthorityError", "ConfigurationError"]


class NECSTAuthorityError(Exception):
    """Error related to controlling priority.

    Examples
    --------
    >>> raise neclib.NECSTAuthorityError("reason or advise to fix this error")

    """

    pass


class ConfigurationError(Exception):
    """Error related to parameter configuration."""

    pass
