"""General operations and core object model definitions of NECLIB.

Warning
-------
The implementations in this namespace should not depend on any other NECLIB subpackages,
since such dependencies would create circular imports.

"""

from . import environ  # noqa: F401
from . import formatting  # noqa: F401
from . import logic  # noqa: F401
from . import type_aliases  # noqa: F401
from . import units  # noqa: F401
from .configuration import *  # noqa: F401, F403
from .data_type import *  # noqa: F401, F403
from .exceptions import *  # noqa: F401, F403
from .files import *  # noqa: F401, F403
from .inform import *  # noqa: F401, F403
from .type_normalization import *  # noqa: F401, F403
