"""Pointing error correction."""

from typing import Iterable, Tuple, Union
import astropy.units as u
from .parser import PointingErrorData


class PointingError(PointingErrorData):
    """Observation pointing error parameter calculator.

    Examples
    --------
    >>> params = neclib.parameters.PointingError.from_file("path/to/params.toml")
    >>> params.refracted2encoder(az=[10, 20, 30], el=[20, 30, 40], unit="deg")
    (<Quantity [11.3, 21.3, 31.3] deg>, <Quantity [20.5, 30.5, 40.5] deg>)
    >>> params.encoder2refracted(
    ...     az=Quantity([10, 20, 30], unit="deg"), el=Quantity([20, 30, 40], unit="deg")
    ... )
    (<Quantity [11.3, 21.3, 31.3] deg>, <Quantity [20.5, 30.5, 40.5] deg>)
    >>> params.encoder2refracted(
    ...     az=Quantity([10, 20, 30], unit="deg"),
    ...     el=Quantity([20, 30, 40], unit="deg"),
    ...     unit="arcsec"
    ... )
    (<Quantity [40680., 76680., 112680.] arcsec>, <Quantity [73800., 109800., 145800.] arcsec>)

    """  # noqa: E501

    def refracted2encoder(
        self,
        az: Union[u.Quantity, Iterable[float]],
        el: Union[u.Quantity, Iterable[float]],
        *,
        unit: Union[str, u.Unit] = None,
    ) -> Tuple[u.Quantity, u.Quantity]:
        unit_is_given = hasattr(az, "unit") and hasattr(el, "unit")
        if (unit is None) and (not unit_is_given):
            raise ValueError("Specify az and el unit.")
        enc_az, enc_el = az, el  # TODO: Implement the calculation.
        return enc_az, enc_el

    def encoder2refracted(
        self,
        az: Union[u.Quantity, Iterable[float]],
        el: Union[u.Quantity, Iterable[float]],
        *,
        unit: Union[str, u.Unit] = None,
    ) -> Tuple[u.Quantity, u.Quantity]:
        unit_is_given = hasattr(az, "unit") and hasattr(el, "unit")
        if (unit is None) and (not unit_is_given):
            raise ValueError("Specify az and el unit.")
        ref_az, ref_el = az, el  # TODO: Implement the calculation.
        return ref_az, ref_el
