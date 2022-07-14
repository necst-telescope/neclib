"""Pointing error correction."""

__all__ = ["PointingError"]

from typing import Iterable, Tuple, Union

import astropy.units as u
import numpy as np

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

    def _get_offset(
        self, az: u.Quantity, el: u.Quantity
    ) -> Tuple[u.Quantity, u.Quantity]:
        """Error from calculated coordinates to encoder reading."""
        gravitational_term = np.polynomial.Polynomial(
            [self.g, self.gg, self.ggg, self.gggg]
        )
        radio_gravitational_term = np.polynomial.Polynomial(
            [self.g_radio, self.gg_radio, self.ggg_radio, self.gggg_radio]
        )

        dx = (
            self.chi_Az * np.sin(self.omega_Az - az) * np.sin(el)
            + self.eps * np.sin(el)
            + self.chi2_Az * np.sin(2 * (self.omega2_Az - az)) * np.sin(el)
            + self.dAz * np.cos(el)
            + self.de
            + self.cor_v * np.cos(el + self.cor_p)
            + self.de_radio
        )
        dAz = dx / np.cos(el)
        dEl = (
            -1 * self.chi_El * np.cos(self.omega_El - az)
            - self.chi2_El * np.cos(2 * (self.omega2_El - az))
            + gravitational_term(el.to("deg").value) * u.deg  # TODO: Review dimension
            + self.dEl
            + radio_gravitational_term(el.to("deg").value)
            * u.deg  # TODO: Review dimension
            - self.cor_v * np.sin(el + self.cor_p)
            + self.del_radio
        )
        return dAz, dEl

    def _force_data_to_be_quantity(
        self,
        data: Union[u.Quantity, float, Iterable[float]],
        unit: Union[str, u.Unit] = None,
    ) -> u.Quantity:
        if isinstance(data, u.Quantity):
            return data if unit is None else data.to(unit)
        return u.Quantity(data, unit=unit)

    def refracted2encoder(
        self,
        az: Union[u.Quantity, float, Iterable[float]],
        el: Union[u.Quantity, float, Iterable[float]],
        *,
        unit: Union[str, u.Unit] = None,
    ) -> Tuple[u.Quantity, u.Quantity]:
        az = self._force_data_to_be_quantity(az, unit)
        el = self._force_data_to_be_quantity(el, unit)
        dAz, dEl = self._get_offset(az, el)
        return az - dAz, el - dEl

    def encoder2refracted(
        self,
        az: Union[u.Quantity, float, Iterable[float]],
        el: Union[u.Quantity, float, Iterable[float]],
        *,
        unit: Union[str, u.Unit] = None,
    ) -> Tuple[u.Quantity, u.Quantity]:
        az = self._force_data_to_be_quantity(az, unit)
        el = self._force_data_to_be_quantity(el, unit)
        dAz, dEl = self._get_offset(az, el)
        return az + dAz, el + dEl
