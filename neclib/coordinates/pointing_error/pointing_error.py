__all__ = ["PointingError"]

import importlib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional, Tuple, Union, overload

import astropy.units as u

from ...core import Parameters, get_quantity
from ...core.types import DimensionLess, UnitType


class PointingError(Parameters, ABC):
    """Calculate pointing error offset.

    Parameters
    ----------
    model
        Name of the pointing error model. If not specified, a dummy class which performs
        no pointing correction will be returned.
    **kwargs
        Model specific parameters.

    Notes
    -----
    This class automatically determines which pointing model to use based on the
    ``model`` argument, so you don't have to import observatory-specific subclass. The
    ``model`` can be specified in TOML file as well.

    Examples
    --------
    >>> pointing_error = neclib.parameters.PointingError.from_file(
    ...     "path/to/pointing_error.toml"
    ... )
    >>> pointing_error.apparent_to_refracted(0 * u.deg, 45 * u.deg)
    (<Quantity 0.1 deg>, <Quantity 45.5 deg>)
    >>> pointing_error.refracted_to_apparent(0 * u.deg, 45 * u.deg)
    (<Quantity -0.1 deg>, <Quantity 44.5 deg>)

    """

    @staticmethod
    def _normalize(key: str, /) -> str:
        return key.lower().replace("_", "")

    def __new__(cls, *, model: Optional[str] = None, **kwargs):
        if model is None:
            raise TypeError(
                f"Cannot instantiate abstract class {cls.__name__!r}. If you need a "
                "dummy version of this class, use `get_dummy` method."
            )

        model = cls._normalize(model)
        if model == cls._normalize(cls.__name__):
            return super().__new__(cls)

        subcls = {cls._normalize(v.__name__): v for v in cls.__subclasses__()}
        if model in subcls:
            return subcls[model](model=model, **kwargs)
        raise ValueError(
            f"Unknown pointing model: {model!r}\n"
            f"Supported ones are: {list(subcls.keys())}"
        )

    @classmethod
    def get_dummy(cls) -> "PointingError":
        """Return a dummy pointing error model which performs no correction.

        Examples
        --------
        >>> pointing_error = neclib.parameters.PointingError.get_dummy()
        >>> pointing_error.apparent_to_refracted(0 * u.deg, 45 * u.deg)
        (<Quantity 0. deg>, <Quantity 45. deg>)

        """

        class Dummy(PointingError):
            def fit(self, *args, **kwargs) -> Any:
                ...

            def offset(
                self, az: u.Quantity, el: u.Quantity
            ) -> Tuple[u.Quantity, u.Quantity]:
                return 0 * u.deg, 0 * u.deg  # type: ignore

        return Dummy(model="dummy")

    @abstractmethod
    def fit(self, *args, **kwargs) -> Any:
        """Fit the model to the measured pointing error parameters."""
        ...

    @abstractmethod
    def offset(self, az: u.Quantity, el: u.Quantity) -> Tuple[u.Quantity, u.Quantity]:
        """Compute the pointing error offset.

        Parameters
        ----------
        az
            Azimuth at which the pointing error is computed.
        el
            Elevation at which the pointing error is computed.

        Returns
        -------
        dAz
            Offset in azimuth axis.
        dEl
            Offset in elevation axis.

        Important
        ---------
        The offset will be ADDED to encoder readings to convert it to true sky/celestial
        coordinate.

        """
        ...

    @overload
    def apparent_to_refracted(
        self, az: u.Quantity, el: u.Quantity, unit: Optional[UnitType] = None
    ) -> Tuple[u.Quantity, u.Quantity]:
        ...

    @overload
    def apparent_to_refracted(
        self, az: DimensionLess, el: DimensionLess, unit: UnitType
    ) -> Tuple[u.Quantity, u.Quantity]:
        ...

    def apparent_to_refracted(
        self,
        az: Union[u.Quantity, DimensionLess],
        el: Union[u.Quantity, DimensionLess],
        unit: Optional[UnitType] = None,
    ) -> Tuple[u.Quantity, u.Quantity]:
        """Convert apparent AltAz coordinate to true coordinate.

        Parameters
        ----------
        az
            Apparent azimuth, which may not accurate due to pointing/instrumental error.
        el
            Apparent elevation, which may not accurate due to pointing/instrumental
            error.
        unit
            Unit of the input azimuth and elevation.

        Returns
        -------
        az
            True azimuth.
        el
            True elevation. Atmospheric refraction should be taken into account, when
            converting this to sky/celestial coordinate.

        Examples
        --------
        >>> pointing_error = neclib.parameters.PointingError.from_file(
        ...     "path/to/pointing_error.toml"
        ... )
        >>> pointing_error.apparent_to_refracted(0 * u.deg, 45 * u.deg)
        (<Quantity 0.1 deg>, <Quantity 45.5 deg>)

        """
        _az, _el = get_quantity(az, el, unit=unit)
        dAz, dEl = self.offset(_az, _el)
        return _az + dAz, _el + dEl

    @overload
    def refracted_to_apparent(
        self, az: u.Quantity, el: u.Quantity, unit: Optional[UnitType] = None
    ) -> Tuple[u.Quantity, u.Quantity]:
        ...

    @overload
    def refracted_to_apparent(
        self, az: DimensionLess, el: DimensionLess, unit: UnitType
    ) -> Tuple[u.Quantity, u.Quantity]:
        ...

    def refracted_to_apparent(
        self,
        az: Union[u.Quantity, DimensionLess],
        el: Union[u.Quantity, DimensionLess],
        unit: Optional[UnitType] = None,
    ) -> Tuple[u.Quantity, u.Quantity]:
        """Convert true sky/celestial coordinate to apparent AltAz coordinate.

        Parameters
        ----------
        az
            True azimuth.
        el
            True elevation. Atmospheric refraction should be taken into account before
            passing to this method.
        unit
            Unit of the input azimuth and elevation.

        Returns
        -------
        az
            Apparent azimuth, with pointing/instrumental error taken into account.
        el
            Apparent elevation, with pointing/instrumental error taken into account.

        Examples
        --------
        >>> pointing_error = neclib.parameters.PointingError.from_file(
        ...     "path/to/pointing_error.toml"
        ... )
        >>> pointing_error.refracted_to_apparent(0 * u.deg, 45 * u.deg)
        (<Quantity -0.1 deg>, <Quantity 44.5 deg>)

        """
        _az, _el = get_quantity(az, el, unit=unit)
        dAz, dEl = self.offset(_az, _el)
        return _az - dAz, _el - dEl


# Import all `PointingError` subclasses, to make them available in
# `PointingError.__subclasses__()` which is called in `PointingError.__new__()`.
impl = Path(__file__).parent.glob("*.py")
for p in impl:
    if p.name.startswith("_") or p.name == __file__:
        continue
    importlib.import_module(f"{__name__.rsplit('.', 1)[0]}.{p.stem}")
