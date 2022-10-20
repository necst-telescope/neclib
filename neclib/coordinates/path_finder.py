__all__ = ["PathFinder"]

import time
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
        ...