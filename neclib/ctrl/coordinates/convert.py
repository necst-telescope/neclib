from pathlib import Path
from typing import TypeVar, Union

import astropy.units as u
import numpy as np
from astropy.coordinates import BaseCoordinateFrame, EarthLocation
from astropy.time import Time


T = TypeVar("T", float, np.ndarray, u.Quantity)
# lon と lat の型が揃っていない場合には対応しなくていい

Number = Union[int, float, np.ndarray]
PathLike = Union[str, bytes, Path]


class CoordCalculator:
    def __init__(
        self,
        location: EarthLocation,
        pointing_param_path: PathLike,
        *,
        pressure: u.Quantity = None,
        temperature: u.Quantity = None,
        relative_humidity: Union[Number, u.Quantity] = None,
        obswl: u.Quantity = None,
    ) -> None:
        # pressure, temperature, relative_humidity, obswl のいずれかが指定されていなかったら logging で warning
        ...

    def update_weather(
        self, 
        pressure: u.Quantity = None,
        temperature: u.Quantity = None,
        relative_humidity: Union[Number, u.Quantity] = None,
    ) -> None:
        ...

    def get_horizontal_by_name(
        self,
        name: str,
        *,
        obstime: Union[Number, Time],
    ) -> u.Quantity:
        ...

    def get_horizontal(
        self,
        lon: T,
        lat: T,
        frame: Union[str, BaseCoordinateFrame],
        *,
        unit: Union[str, u.Unit] = None,
        obstime: Union[Number, Time],
    ) -> u.Quantity:
        # T が u.Quantity でなければ unit 指定必須
        # T が u.Quantity ならば unit に変換して返す
        ...