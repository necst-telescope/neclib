__all__ = ["PathFinder"]

import math
from typing import List, Tuple, TypeVar, Union

import astropy.constants as const
import astropy.units as u
from astropy.coordinates import (
    BaseCoordinateFrame,
    EarthLocation,
)
from astropy.time import Time

from .convert import CoordCalculator
from .. import config, get_logger, utils
from ..parameters.pointing_error import PointingError
from ..typing import Number, PathLike


T = TypeVar("T", Number, u.Quantity) # lon, lat の型


class PathFinder:
    """望遠鏡の軌道を計算する

    Parameters
    ----------
    location
        Location of observatory.
    pointing_param_path
        Path to pointing parameter file.
    pressure
        Atmospheric pressure at the observation environment.
    temperature
        Temperature at the observation environment.
    relative_humidity
        Relative humidity at the observation environment.
    obswl
        Observing wavelength.

    Attributes
    ----------
    location: EarthLocation
        Location of observatory.
    pressure: Quantity
        Atmospheric pressure, to compute diffraction correction.
    temperature: Quantity
        Temperature, to compute diffraction correction.
    relative_humidity: Quantity or float
        Relative humidity, to compute diffraction correction.
    obswl: Quantity
        Observing wavelength, to compute diffraction correction.
    obsfreq: Quantity
        Observing frequency of EM-wave, to compute diffraction correction.

    Examples
    --------
    >>> location = EarthLocation("138.472153deg", "35.940874deg", "1386m")
    >>> path = "path/to/pointing_param.toml"
    >>> pressure = 850 * u.hPa
    >>> temperature = 290 * u.K
    >>> humid = 0.5
    >>> obsfreq = 230 * u.GHz
    >>> finder = neclib.coordinates.PathFinder(
    ...     location, path, pressure=pressure, temperature=temperature,
    ...     relative_humidity=humid, obsfreq=obsfreq)

    """

    def __init__(
        self,
        location: EarthLocation,
        pointing_param_path: PathLike,
        *,  # 以降の引数はキーワード引数（引数名=値）として受け取ることを強制する
        pressure: u.Quantity = None,
        temperature: u.Quantity = None,
        relative_humidity: Union[Number, u.Quantity] = None,
        obswl: u.Quantity = None,
        obsfreq: u.Quantity = None,
    ) -> None:
        self.logger = get_logger(self.__class__.__name__)

        if (obswl is not None) and (obsfreq is not None):
            if obswl != const.c / obsfreq:
                raise ValueError("Specify ``obswl`` or ``obs_freq``, not both.")

        self.location = location
        self.pointing_param_path = pointing_param_path
        self.pressure = pressure
        self.temperature = temperature
        self.relative_humidity = relative_humidity
        self.obswl = obswl
        if temperature is not None:
            self.temperature = temperature.to("deg_C", equivalencies=u.temperature())
        if obsfreq is not None:
            self.obswl = const.c / obsfreq

        self.pointing_error_corrector = PointingError.from_file(pointing_param_path)

        diffraction_params = ["pressure", "temperature", "relative_humidity", "obswl"]
        not_set = list(filter(lambda x: getattr(self, x) is None, diffraction_params))
        if len(not_set) > 0:
            self.logger.warning(
                f"{not_set} are not set. Diffraction correction is not available."
            )
    
    def linear(
        self,
        start: Tuple[T, T],
        end: Tuple[T, T],
        frame: Union[str, BaseCoordinateFrame],
        speed: Union[float, int, u.Quantity],
        *,
        unit: Union[str, u.Unit] = None,
        obstime: Union[Number, Time] = None
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
        obstime
            Time the observation is started.

        Examples
        --------
        >>> finder.linear(start=(0, 0), end=(0.05, 0), frame="altaz", speed=0.5, unit=u.deg, obstime=1000)
        [0, 0.01, 0.02, 0.03, 0.04, 0.05] * u.deg, [0, 0, 0, 0, 0, 0] * u.deg, [1000, 1000.02, 1000.04, 1000.06, 1000.08, 1000.1],

        """
        try:
            start_time = float(obstime)
        except TypeError:
            start_time = (obstime.to("second")).value
        try:
            speed = float(speed)
        except TypeError:
            pass
        else:
            speed *= u.deg / u.second
        frequency = config.antenna_command_frequency
        offset = config.antenna_command_offset_sec
        start_lon, start_lat = utils.get_quantity(start[0], start[1], unit=unit)
        end_lon, end_lat = utils.get_quantity(end_lon, end_lat, unit=unit)
        required_time = max(abs(end_lon-start_lon), abs(end_lat-start_lat)) / speed
        required_time = (required_time.to("second")).value
        command_num = math.ceil(required_time*frequency)
        required_time = command_num / frequency
        command_num += 1 # 始点の分を追加
        calculator = CoordCalculator(
            location = self.location,
            pointing_param_path = self.pointing_param_path,
            pressure = self.pressure,
            temperature = self.temperature,
            relative_humidity = self.relative_humidity,
            obswl = self.obswl,
        )
        start_altaz = calculator.get_altaz(lon=start_lon, lat=start_lat, frame=frame, unit=unit, obstime=start_time)
        end_altaz = calculator.get_altaz(lon=end_lon, lat=end_lat, frame=frame, unit=unit, obstime=start_time+required_time)
        return_unit = (start_altaz.az).unit
        start_altaz.az = (start_altaz.az).value
        start_altaz.alt = (start_altaz.alt).value
        end_altaz.az = (end_altaz.az).value
        end_altaz.alt = (end_altaz.alt).value
        az = [start_altaz.az + (end_altaz.az-start_altaz.az) * i / (command_num-1) for i in range(command_num)] * return_unit
        az[command_num-1] = end_altaz.az
        el = [start_altaz.alt + (end_altaz.alt-start_altaz.alt) * i / (command_num-1) for i in range(command_num)] * return_unit
        el[command_num-1] = end_altaz.alt
        t = [start_time + offset + i / frequency for i in range(command_num)]
        return (az, el, t)