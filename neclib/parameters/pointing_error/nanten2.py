from typing import Tuple

import astropy.units as u
import numpy as np
from astropy.coordinates import Angle

from .pointing_error import PointingError


class NANTEN2(PointingError):
    r"""Pointing model used in NANTEN2.

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

    dAz: Angle = 0 << u.arcsec
    """Azimuth (not X) offset of encoder reading."""
    de: Angle = 0 << u.arcsec
    """X collimation error."""
    chi_Az: Angle = 0 << u.arcsec
    """Magnitude of tilt of azimuth axis."""
    omega_Az: Angle = 0 << u.deg
    """Phase (azimuth direction) of tilt of azimuth axis."""
    eps: Angle = 0 << u.arcsec
    """Skew angle (lack of orthogonality) between azimuth and elevation axes."""
    chi2_Az: Angle = 0 << u.arcsec
    """Same as chi, but the period is 180deg in azimuth axis (harmonic component)."""
    omega2_Az: Angle = 0 << u.deg
    """Same as omega, but the period is 180deg in azimuth (harmonic component)."""
    chi_El: Angle = 0 << u.arcsec
    """Amplitude of tilt of azimuth axis (same as chi_Az)."""
    omega_El: Angle = 0 << u.deg
    """Phase (azimuth direction) of tilt of azimuth axis (same as omega_Az)."""
    chi2_El: Angle = 0 << u.arcsec
    """Same as chi, but the period is 180deg in azimuth axis (harmonic component, same
    as chi2_Az)."""
    omega2_El: Angle = 0 << u.deg
    """Same as omega, but the period is 180deg in azimuth (harmonic component, same as
    omega2_Az)."""
    g: float = 0
    """First order gravitational deflection coefficient."""
    gg: float = 0
    """Second order gravitational deflection coefficient."""
    ggg: float = 0
    """Third order gravitational deflection coefficient."""
    gggg: float = 0
    """Fourth order gravitational deflection coefficient."""
    dEl: Angle = 0 << u.arcsec
    """Elevation offset of encoder reading."""
    de_radio: Angle = 0 << u.arcsec
    """Constant X (not azimuth) offset between optical and radio beam."""
    del_radio: Angle = 0 << u.arcsec
    """Constant elevation offset between optical and radio beam."""
    cor_v: Angle = 0 << u.arcsec
    """Amplitude of collimation error."""
    cor_p: Angle = 0 << u.deg
    """Phase of collimation error, negative of elevation where the elevation component
    of collimation error is zero."""
    g_radio: float = 0
    """First order gravitational deflection coefficient."""
    gg_radio: float = 0
    """Second order gravitational deflection coefficient."""
    ggg_radio: float = 0
    """Third order gravitational deflection coefficient."""
    gggg_radio: float = 0
    """Fourth order gravitational deflection coefficient."""

    def offset(self, az: u.Quantity, el: u.Quantity) -> Tuple[u.Quantity, u.Quantity]:
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
            + gravitational_term(el.to_value("deg")) * u.arcsec
            + self.dEl
            + radio_gravitational_term(el.to_value("deg")) * u.arcsec
            - self.cor_v * np.sin(el + self.cor_p)
            + self.del_radio
        )  # NOTE: 2nd term: chi2 cos, revised from chi2 sin
        # TODO: Review dimension of gravitational terms
        return dAz, dEl

    def fit(self, *args, **kwargs):
        raise NotImplementedError("Fitting is not implemented for this model.")
