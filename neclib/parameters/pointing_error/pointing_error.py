"""Pointing error correction.

The telescope pointing is critically important in performing accurate and uniform
observation.

"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, fields
from typing import Optional, Tuple, final

import astropy.units as u
import tomlkit
from astropy.coordinates import Angle
from tomlkit.exceptions import UnexpectedCharError

from .. import utils
from ..typing import QuantityValue, UnitType


@dataclass
class PointingError(ABC):

    model: str
    file: Optional[os.PathLike] = None

    def __new__(cls, model: str, **kwargs):
        model = utils.toCamelCase(model).lower()
        if model == cls.__name__.lower():
            return super().__new__(cls)

        subcls = {v.__name__.lower(): v for v in cls.__subclasses__()}
        if model in subcls:
            return dataclass(subcls[model])(model, **kwargs)
        raise TypeError(
            f"Unknown pointing model: {model!r}; supported: {list(subcls.keys())}"
        )

    @final
    @classmethod
    def from_file(cls, filename: os.PathLike, model: Optional[str] = None, **kwargs):
        contents = utils.read_file(filename)
        kwargs.update({"file": filename})
        try:
            parsed = tomlkit.parse(contents)
            model = model or parsed.get("model", None)
            parsed = parsed.get("pointing_params", parsed)
            quantities = {}
            for k, v in parsed.items():
                if v == {}:  # Empty value.
                    quantities[k] = None
                    continue
                try:
                    quantities[k] = Angle(v)
                except (u.UnitsError, u.UnitTypeError, ValueError):
                    quantities[k] = u.Quantity(v)
                    # Boolean values can be parsed as quantities, but we currently don't
                    # expect such values to be in the pointing model parameters.
                except TypeError:
                    quantities[k] = v
        except UnexpectedCharError:
            parsed_to = cls(model).__class__
            units = {
                f.name: getattr(f.default, "unit", u.dimensionless_unscaled)
                for f in fields(parsed_to)[2:]  # Not 'model' or 'file'
            }
            normalized_contents = filter(lambda x: x.strip(), contents.split("\n"))
            quantities = {
                k: float(v) * unit
                for (k, unit), v in zip(units.items(), normalized_contents)
            }
        return cls(model, **quantities, **kwargs)

    def __getitem__(self, key):
        if key in (f.name for f in fields(self)):
            return getattr(self, key)

    @abstractmethod
    def fit(self, *args, **kwargs):
        """Fit the model to the data."""
        ...

    @abstractmethod
    def offset(self, az: u.Quantity, el: u.Quantity) -> Tuple[u.Quantity, u.Quantity]:
        ...

    def apparent2refracted(
        self, az: QuantityValue, el: QuantityValue, unit: Optional[UnitType] = None
    ) -> Tuple[u.Quantity, u.Quantity]:
        az, el = utils.get_quantity(az, el, unit=unit)
        dAz, dEl = self.offset(az, el)
        return az + dAz, el + dEl

    def refracted2apparent(
        self, az: QuantityValue, el: QuantityValue, unit: Optional[UnitType] = None
    ) -> Tuple[u.Quantity, u.Quantity]:
        az, el = utils.get_quantity(az, el, unit=unit)
        dAz, dEl = self.offset(az, el)
        return az - dAz, el - dEl
