__all__ = ["exceptions"]


from ..core import deprecated_namespace
from ..core import exceptions as core_exceptions

exceptions = deprecated_namespace(
    core_exceptions,
    "neclib.exceptions",
    version_since="0.22.0",
    version_removed="1.0.0",
    replacement="neclib.core.exceptions",
)
