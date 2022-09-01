from pathlib import Path
from typing import TypeVar, Union
import logging

import astropy.units as u
import numpy as np
from astropy.coordinates import BaseCoordinateFrame, EarthLocation, SkyCoord, ICRS, Galactic, FK4, FK5, AltAz
from astropy.time import Time


T = TypeVar("T", float, np.ndarray, u.Quantity)
# lon と lat の型が揃っていない場合には対応しなくていい

Number = Union[int, float, np.ndarray] # int または float または np.ndarray
PathLike = Union[str, bytes, Path]


class CoordCalculator:
    def __init__(
        self,
        location: EarthLocation,
        pointing_param_path: PathLike,
        *, # 以降の引数はキーワード引数（引数名=値）として受け取ることを強制する
        pressure: u.Quantity = None,
        temperature: u.Quantity = None,
        relative_humidity: Union[Number, u.Quantity] = None,
        obswl: u.Quantity = None,
    ) -> None:
        self.location = location
        self.pointing_param_path = pointing_param_path
        self.pressure = pressure
        self.temperature = temperature
        self.relative_humidity = relative_humidity
        self.obswl = obswl
        # pressure, temperature, relative_humidity, obswl のいずれかが指定されていなかったら logging で warning
        logger = logging.getLogger(__name__)
        if pressure is None:
            logger.warning("pressure が未指定です。")
        if temperature is None:
            logger.warning("temperature が未指定です。")
        if relative_humidity is None:
            logger.warning("relative_humidity が未指定です。")
        if obswl is None:
            logger.warning("obswl が未指定です。")

    def update_weather(
        self, 
        pressure: u.Quantity = None,
        temperature: u.Quantity = None,
        relative_humidity: Union[Number, u.Quantity] = None,
    ) -> None:
        """気象情報を更新する"""
        self.pressure = pressure
        self.temperature = temperature
        self.relative_humidity = relative_humidity

    def get_horizontal_by_name(
        self,
        name: str,
        *,
        obstime: Union[Number, Time],
    ) -> u.Quantity:
        """天体名から地平座標 az, el(alt) を取得する"""
        radec = SkyCoord.from_name(name)
        altaz = radec.transform_to(AltAz(
            obstime = obstime,
            location = self.location,
            pressure = self.pressure,
            temperature = self.temperature,
            relative_humidity = self.relative_humidity,
            obswl = self.obswl,
        ))
        return altaz.az, altaz.alt

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