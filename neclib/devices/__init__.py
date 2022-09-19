import sys
from . import selector

from . import encoder
from . import motor


impl_modules = [encoder, motor]
implementations = selector.list_implementations(impl_modules)
parsed = selector.parse_device_configuration(impl_modules)
here = sys.modules[__name__]
_ = [setattr(here, k, v) for k, v in parsed.items()]
