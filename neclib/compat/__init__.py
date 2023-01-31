__all__ = ["exceptions"]


from ..core import deprecated_namespace
from ..core import exceptions as core_exceptions
from ..core import inform, type_aliases

exceptions = deprecated_namespace(
    core_exceptions,
    "neclib.exceptions",
    version_since="0.22.0",
    version_removed="1.0.0",
    replacement="neclib.core.exceptions",
)
typing = deprecated_namespace(
    type_aliases,
    "neclib.typing",
    version_since="0.22.0",
    version_removed="1.0.0",
    replacement="neclib.core.type_aliases",
)
interfaces = deprecated_namespace(
    inform,
    "neclib.interfaces",
    version_since="0.22.0",
    version_removed="1.0.0",
    replacement="neclib.core.inform",
)
