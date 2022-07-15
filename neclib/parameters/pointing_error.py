r"""Pointing error correction.

The telescope pointing is critically important in performing accurate and uniform
observation. This module employs following pointing model:

.. math::

    \Delta x =& \chi_{Az} \sin ( \omega_{Az} - Az ) \sin ( El ) \\
    &+ \epsilon \sin ( El ) \\
    &+ \chi_{2, Az} \sin ( 2 ( \omega_{2, Az} - Az ) ) \sin ( El ) \\
    &+ \mathrm{d}Az \cos ( El ) \\
    &+ \mathrm{d}e \\
    &+ \mathrm{cor}_v \cos ( El + \mathrm{cor}_p ) \\
    &+ \mathrm{d}e_\mathrm{radio} \\
    \Delta Az =& \Delta x / \cos ( El ) \\
    \Delta y =& - \chi_{El} \cos ( \omega_{El} - Az ) \\
    &- \chi_{2, El} \cos ( 2 ( \omega_{2, El} - Az ) ) \\
    &+ g_1 \cos ( El ) + g_2 \sin ( El ) \\
    &+ \mathrm{d}el \\
    &+ g_{ 1,\mathrm{radio} } \cos ( El ) + g_{ 2,\mathrm{radio} } \sin ( El ) \\
    &- \mathrm{cor}_v \sin ( El + \mathrm{cor}_p ) \\
    &+ \mathrm{d}el_\mathrm{radio} \\
    \Delta El =& \Delta y

"""

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
            [0, self.g, self.gg, self.ggg, self.gggg]
        )
        radio_gravitational_term = np.polynomial.Polynomial(
            [0, self.g_radio, self.gg_radio, self.ggg_radio, self.gggg_radio]
        )

        dx = (
            self.chi_Az * np.sin(self.omega_Az - az) * np.sin(el)
            + self.eps * np.sin(el)
            + self.chi2_Az * np.sin(2 * (self.omega2_Az - az)) * np.sin(el)
            + self.dAz * np.cos(el)
            + self.de
            + self.cor_v * np.cos(el + self.cor_p)
            + self.de_radio
        )  # NOTE: 3rd term: chi2 sin sin, revised from chi2 cos sin
        dAz = dx / np.cos(el)
        dEl = (
            -1 * self.chi_El * np.cos(self.omega_El - az)
            - self.chi2_El * np.cos(2 * (self.omega2_El - az))
            + gravitational_term(el.to("deg").value) * u.arcsec
            + self.dEl
            + radio_gravitational_term(el.to("deg").value) * u.arcsec
            - self.cor_v * np.sin(el + self.cor_p)
            + self.del_radio
        )  # NOTE: 2nd term: chi2 cos, revised from chi2 sin
        # TODO: Review dimension of gravitational terms
        print(dAz.to("arcsec"), dEl.to("arcsec"), sep="\n")
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
