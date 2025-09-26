from typing import Tuple

import astropy.units as u
import numpy as np
import scipy

from .pointing_error import PointingError


class NANTEN2(PointingError):
    r"""Pointing model used in NANTEN2.

    .. math::

        \Delta x =& \chi_{Az} \sin ( \omega_{Az} - Az ) \sin ( El ) \\
        &+ \epsilon \sin ( El ) \\
        &+ \chi_{2, Az} \sin ( 2 ( \omega_{2, Az} - Az ) ) \sin ( El ) \\
        &+ \mathrm{d}Az \cos ( El ) \\
        &+ \mathrm{d}e \\
        &+ cor_\mathrm{v} \cos ( El + cor_\mathrm{p} ) \\
        &+ \mathrm{d}e_\mathrm{radio} \\
        \Delta Az =& \Delta x / \cos ( El ) \\
        \Delta y =& - \chi_{El} \cos ( \omega_{El} - Az ) \\
        &- \chi_{2, El} \cos ( 2 ( \omega_{2, El} - Az ) ) \\
        &+ g_1 \cos ( El ) + g_2 \sin ( El ) \\
        &+ \mathrm{d}el \\
        &+ g_{ 1,\mathrm{radio} } \cos ( El ) + g_{ 2,\mathrm{radio} } \sin ( El ) \\
        &- cor_\mathrm{v} \sin ( El + cor_\mathrm{p} ) \\
        &+ \mathrm{d}el_\mathrm{radio} \\
        \Delta El =& \Delta y

    Parameters
    ----------
    dAz
        Azimuth (not X) offset of encoder reading.
    de
        X collimation error.
    chi_Az
        Magnitude of tilt of azimuth axis.
    omega_Az
        Phase (azimuth direction) of tilt of azimuth axis.
    eps
        Skew angle (lack of orthogonality) between azimuth and elevation axes.
    chi2_Az
        Same as chi, but the period is 180deg in azimuth axis (harmonic component).
    omega2_Az
        Same as omega, but the period is 180deg in azimuth (harmonic component).
    chi_El
        Magnitude of tilt of elevation axis.
    omega_El
        Phase (azimuth direction) of tilt of elevation axis.
    chi2_El
        Same as chi, but the period is 180deg in azimuth axis (harmonic component).
    omega2_El
        Same as omega, but the period is 180deg in azimuth (harmonic component).
    g
        First order gravitational deflection coefficient.
    gg
        Second order gravitational deflection coefficient.
    ggg
        Third order gravitational deflection coefficient.
    gggg
        Fourth order gravitational deflection coefficient.
    dEl: Angle = 0 << u.arcsec
        Elevation offset of encoder reading.
    de_radio: Angle = 0 << u.arcsec
        Constant X (not azimuth) offset between optical and radio beam.
    del_radio: Angle = 0 << u.arcsec
        Constant elevation offset between optical and radio beam.
    cor_v: Angle = 0 << u.arcsec
        Amplitude of collimation error.
    cor_p: Angle = 0 << u.deg
        Phase of collimation error, negative of elevation where the elevation component
        of collimation error is zero.
    g_radio: float = 0
        First order gravitational deflection coefficient.
    gg_radio: float = 0
        Second order gravitational deflection coefficient.
    ggg_radio: float = 0
        Third order gravitational deflection coefficient.
    gggg_radio: float = 0
        Fourth order gravitational deflection coefficient.

    """

    def apply_offset(
        self, az: u.Quantity, el: u.Quantity
    ) -> Tuple[u.Quantity, u.Quantity]:
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
        return az - dAz, el - dEl

    def apply_inverse_offset(
        self, az: u.Quantity, el: u.Quantity
    ) -> Tuple[u.Quantity, u.Quantity]:
        gravitational_term = np.polynomial.Polynomial(
            [0, self.g, self.gg, self.ggg, self.gggg]
        )
        radio_gravitational_term = np.polynomial.Polynomial(
            [0, self.g_radio, self.gg_radio, self.ggg_radio, self.gggg_radio]
        )

        def res(x):
            Az0 = az.value
            El0 = el.value
            chi_Az = self.chi_Az.deg
            eps = self.eps.value
            chi2_Az = self.chi2_Az.deg
            dAz = self.dAz.deg
            de = self.de.deg
            cor_v = self.cor_v.deg
            de_ratio = self.de_ratio.deg
            omega_Az = self.omega_Az.deg
            omega2_Az = self.omega2_Az.deg
            cor_p = self.cor_p.deg
            chi_El = self.chi_El.deg
            chi2_El = self.chi2_El.deg
            dEl = self.dEl.deg
            omega_El = self.omega_El.deg
            omega2_El = self.omega2_El.deg
            del_radio = self.del_radio.deg
            dx = (
                chi_Az
                * np.sin(omega_Az * np.pi / 180)
                * np.cos(x[0] * np.pi / 180)
                * np.sin(x[1] * np.pi / 180)
                - chi_Az
                * np.cos(omega_Az * np.pi / 180)
                * np.sin(x[0] * np.pi / 180)
                * np.sin(x[1] * np.pi / 180)
                + eps * np.sin(x[1] * np.pi / 180)
                + chi2_Az
                * np.sin(2 * omega2_Az * np.pi / 180)
                * np.cos(2 * x[0] * np.pi / 180)
                * np.sin(x[1] * np.pi / 180)
                + chi2_Az
                * np.cos(2 * omega2_Az * np.pi / 180)
                * np.sin(2 * x[0] * np.pi / 180)
                * np.sin(x[1] * np.pi / 180)
                + dAz * np.cos(x[1] * np.pi / 180)
                + de
                + cor_v * np.cos(x[1] * np.pi / 180) * np.cos(cor_p * np.pi / 180)
                + cor_v * np.sin(x[1] * np.pi / 180) * np.sin(cor_p * np.pi / 180)
                + de_ratio
            )

            dy = (
                -1
                * chi_El
                * np.cos(omega_El * np.pi / 180)
                * np.cos(x[0] * np.pi / 180)
                - chi_El * np.sin(omega_El * np.pi / 180) * np.sin(x[0] * np.pi / 180)
                - chi2_El
                * np.cos(2 * omega2_El * np.pi / 180)
                * np.cos(2 * x[0] * np.pi / 180)
                - chi2_El
                * np.sin(2 * omega2_El * np.pi / 180)
                * np.sin(2 * x[0] * np.pi / 180)
                + gravitational_term(x[1]) * u.arcsec
                + dEl
                + radio_gravitational_term(x[1]) * u.arcsec
                - cor_v * np.sin(x[1] * np.pi / 180) * np.cos(cor_p * np.pi / 180)
                - cor_v * np.cos(x[1] * np.pi / 180) * np.sin(cor_p * np.pi / 180)
                + del_radio
            )

            f = np.zeros(2, dtype=float)

            f[0] = (x[0] + (dx / np.cos(x[1] * np.pi / 180)) - Az0) * (
                1
                + (1 / np.cos(x[1] * np.pi / 180))
                * (
                    -chi_Az
                    * np.sin(omega_Az * np.pi / 180)
                    * np.sin(x[0] * np.pi / 180)
                    * np.sin(x[1] * np.pi / 180)
                    - chi_Az
                    * np.cos(omega_Az * np.pi / 180)
                    * np.cos(x[0] * np.pi / 180)
                    * np.sin(x[1] * np.pi / 180)
                    - 2
                    * chi2_Az
                    * np.sin(2 * omega2_Az * np.pi / 180)
                    * np.sin(2 * x[0] * np.pi / 180)
                    * np.sin(x[1] * np.pi / 180)
                    - 2
                    * chi2_Az
                    * np.cos(2 * omega2_Az * np.pi / 180)
                    * np.cos(2 * x[0] * np.pi / 180)
                    * np.sin(x[1] * np.pi / 180)
                )
            ) + (x[1] + dy - El0) * (
                chi_El * np.cos(omega_El * np.pi / 180) * np.sin(x[0] * np.pi / 180)
                - chi_El * np.sin(omega_El * np.pi / 180) * np.cos(x[0] * np.pi / 180)
                + 2
                * chi2_El
                * np.cos(omega2_El * np.pi / 180)
                * np.sin(2 * x[0] * np.pi / 180)
                - 2
                * chi2_El
                * np.sin(omega2_El * np.pi / 180)
                * np.cos(2 * x[0] * np.pi / 180)
            )
            f[1] = (x[0] + (dx / np.cos(x[1] * np.pi / 180)) - Az0) * (
                np.tan(x[1] * np.pi / 180) * dx
                + (1 / np.cos(x[1] * np.pi / 180))
                * (
                    chi_Az
                    * np.sin(omega_Az * np.pi / 180)
                    * np.cos(x[0] * np.pi / 180)
                    * np.cos(x[1] * np.pi / 180)
                    - chi_Az
                    * np.cos(omega_Az * np.pi / 180)
                    * np.sin(x[0] * np.pi / 180)
                    * np.cos(x[1] * np.pi / 180)
                    + eps * np.cos(x[1] * np.pi / 180)
                    + chi2_Az
                    * np.sin(2 * omega2_Az * np.pi / 180)
                    * np.cos(2 * x[0] * np.pi / 180)
                    * np.cos(x[1] * np.pi / 180)
                    - chi2_Az
                    * np.cos(2 * omega2_Az * np.pi / 180)
                    * np.sin(2 * x[0] * np.pi / 180)
                    * np.cos(x[1] * np.pi / 180)
                    - dAz * np.sin(x[1] * np.pi / 180)
                    - cor_v * np.sin(x[1] * np.pi / 180) * np.cos(cor_p * np.pi / 180)
                    + cor_v * np.cos(x[1] * np.pi / 180) * np.cos(cor_p * np.pi / 180)
                )
            ) + (x[1] + dy - El0) * (
                gravitational_term.deriv(1)(x[1])
                + radio_gravitational_term(1)(x[1])
                - cor_v * np.cos(x[1] * np.pi / 180) * np.cos(cor_p * np.pi / 180)
                + cor_v * np.sin(x[1] * np.pi / 180) * np.sin(cor_p * np.pi / 180)
            )
            return f

        az0, el0 = self.apply_offset(az, el)
        x0 = np.array([az0.deg, el0.deg])

        ans = scipy.optimize.root(res, x0, method="hybr", tol=1e-13)
        az, el = ans.x

        return az * u.deg, el * u.deg

    def fit(self, *args, **kwargs):
        raise NotImplementedError("Fitting is not implemented for this model.")
