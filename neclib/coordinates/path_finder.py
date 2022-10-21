__all__ = ["PathFinder"]

import time
import math
from typing import List, Tuple, TypeVar, Union

import astropy.units as u
from astropy.coordinates import (
    AltAz,
    BaseCoordinateFrame,
    EarthLocation,
    SkyCoord,
    get_body,
)
from astropy.time import Time
from numpy import require

from .convert import CoordCalculator
from .. import config, get_logger, utils
from ..parameters.pointing_error import PointingError
from ..typing import Number, PathLike


T = TypeVar("T", Number, u.Quantity) # lon, lat の型


class PathFinder:
    """望遠鏡の軌道を計算する

    Examples
    --------
    >>> finder = neclib.coordinates.PathFinder()

    """

    def __init__(self) -> None:
        pass

    def linear(
        self,
        start: Tuple[T, T],
        end: Tuple[T, T],
        frame: Union[str, BaseCoordinateFrame],
        speed: float,
        *,
        unit: Union[str, u.Unit] = None,
    ) -> Tuple[u.Quantity, u.Quantity, List[float]]: # (Az 配列, El 配列, t 配列)
        """望遠鏡の直線軌道を計算する

        Parameters
        ----------
        start
            Longitude and latitude of start point.
        end
            Longitude and latitude of end point.
        frame
            Coordinate frame, in which longitude and latitude are given.
        speed
            Telescope drive speed.
        unit
            Angular unit in which longitude and latitude are given. If they are given as
            ``Quantity``, this parameter will be ignored.

        Examples
        --------
        >>> finder.linear(start=(0*u.deg, 1*u.deg), end=(0.1*u.deg, 2*u.deg), frame="fk5", speed=1/5)
        ...

        """
        now = time.time()
        frequency = config.antenna_command_frequency
        offset = config.antenna_command_offset_sec
        required_time = max(abs(end[0]-start[0]), abs(end[1]-start[1])) / speed
        command_num = math.ceil(required_time*frequency)
        required_time = command_num / frequency
        command_num += 1 # 始点の分を追加
        calculator = CoordCalculator(
            location = config.location,
            pointing_param_path = config.antenna_pointing_parameter_path,
            # pressure = 850 * u.hPa,
            # temperature = 290 * u.K,
            # relative_humidity = 0.5,
            # obswl = 230 * u.GHz,
        )
        start_altaz = calculator.get_altaz(lon=start[0], lat=start[1], frame=frame, unit=unit, obstime=now)
        end_altaz = calculator.get_altaz(lon=end[0], lat=end[1], frame=frame, unit=unit, obstime=now+required_time)
        az = [start_altaz.az + (end_altaz.az-start_altaz.az) * i / (command_num-1) for i in range(command_num)] # * unit
        az[command_num-1] = end_altaz.az
        el = [start_altaz.alt + (end_altaz.alt-start_altaz.alt) * i / (command_num-1) for i in range(command_num)] # * unit
        el[command_num-1] = end_altaz.alt
        t = [now + offset + i / frequency for i in range(command_num)]
        return (az, el, t)