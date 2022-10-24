import sys
from . import selector

from . import encoder
from . import motor
from . import weather_station


impl_modules = [encoder, motor, weather_station]
implementations = selector.list_implementations(impl_modules)
parsed = selector.parse_device_configuration(impl_modules)
here = sys.modules[__name__]
_ = [setattr(here, k, v) for k, v in parsed.items()]
