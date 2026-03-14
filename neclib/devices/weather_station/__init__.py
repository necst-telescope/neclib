from .simulator import WeatherStationSimulator  # noqa: F401
from .tr72w import TR72W  # noqa: F401
from .tr73u import TR73U  # noqa: F401

try:
    from .vantagepro2 import VantagePro2  # noqa: F401
except ImportError:
    print(
        "You can't import device.vantagepro2.VantagePro2 "
        "because there isn't pyWeather package."
    )
    print(
        "Please install `pyWeather` and run "
        "`pip install git+https://github.com/TakutoIto/PyWeather.git`"
    )
    pass
