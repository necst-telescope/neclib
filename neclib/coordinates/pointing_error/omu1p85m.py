from typing import Tuple

import astropy.units as u
import numpy as np
import scipy

from .pointing_error import PointingError


class OMU1P85M(PointingError):
    r"""Pointing model used in OMU1P85M.

    .. math::

        \Delta x =& a_1 \sin ( El ) \\
        &+ a_2 \\
        &+ a_3 \cos ( El ) \\
        &+ b_1 \sin ( Az ) \sin ( El ) \\
        &- b_2 \cos ( Az ) \sin ( El ) \\
        &+ c_1 * \sin ( Az - El ) \\
        &+ c_2 * \cos ( Az - El ) \\
        &+ d_1 \\
        &+ e_1 \cos ( El ) \\
        &- e_2 \sin ( El ) \\
        \Delta Az =& - \Delta x / \cos ( El ) \\
        \Delta y =& b_1 \cos ( Az ) \\
        &+ b_2 \sin ( Az ) \\
        &+ b_3 \\
        &+ g_1 El \\
        &+ c_1 \cos ( Az - El ) \\
        &- c_2 \sin ( Az - El ) \\
        &+ d_2 \\
        &+ e_1 \sin ( El ) \\
        &+ e_2 \cos ( El ) \\
        \Delta El =& - \Delta y

    Parameters
    ----------
    a1
        Skew angle (lack of orthogonality) between azimuth and elevation axes.
    a2
        X collimation error; non-orthogonality between elevation and optical axes.
    a3
        Azimuth (not X) offset of encoder reading.
    b1
        Tilt angle of azimuth axis, in North-South direction. North-positive.
    b2
        Tilt angle of azimuth axis, in East-West direction. East-positive.
    b3
        Elevation offset of encoder reading.
    g1
        Gravitational deflection coefficient.
    c1
    c2
    d1
    d2
    e1
    e2

    """

    def offset(self, az: u.Quantity, el: u.Quantity) -> Tuple[u.Quantity, u.Quantity]:
        dx = (
            self.a1 * np.sin(el)
            + self.a2
            + self.a3 * np.cos(el)
            + self.b1 * np.sin(az) * np.sin(el)
            - self.b2 * np.cos(az) * np.sin(el)
            + self.c1 * np.sin(az - el)
            + self.c2 * np.cos(az - el)
            + self.d1
            + self.e1 * np.cos(el)
            - self.e2 * np.sin(el)
        )
        dAz = dx / np.cos(el)
        dy = (
            self.b1 * np.cos(az)
            + self.b2 * np.sin(az)
            + self.b3
            + self.g1 * el
            + self.c1 * np.cos(az - el)
            - self.c2 * np.sin(az - el)
            + self.d2
            + self.e1 * np.sin(el)
            + self.e2 * np.cos(el)
        )
        dEl = dy

        # The above is defined as (refracted + offset = apparent), so reverse the sign
        return -1 * dAz, -1 * dEl

    def inverse_offset(
        self, az: u.Quantity, el: u.Quantity
    ) -> Tuple[u.Quantity, u.Quantity]:
        """Convert apparent AltAz coordinate to true coordinate.

        Parameters
        ----------
        az
            Apparent azimuth, which may not accurate due to pointing/instrumental error.
        el
            Apparent elevation, which may not accurate due to pointing/instrumental
            error.
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

        def res(x):
            r"""
            x[0],x[1]
                        True azimath, elevation
            f[0],f[1]
                        \frac{\partial f}{\partial Az}, \ frac{\partial f}{\partial El}

                        f(Az, El)=(Az'(Az, El)-Az'_0)^2+(El'(Az, El)-El'_0)^2

                        (Az', El' is Apparant azimath, elevation of pointing model
                         Az'_0, El'_0 is Apparant azimath, elevation of encoder values)
            """
            Az0 = az.value
            El0 = el.value
            a1 = self.a1.deg
            a2 = self.a2.deg
            a3 = self.a3.deg
            b1 = self.b1.deg
            b2 = self.b2.deg
            b3 = self.b3.deg
            c1 = self.c1.deg
            c2 = self.c2.deg
            d1 = self.d1.deg
            d2 = self.d2.deg
            g1 = self.g1
            e1 = self.e1.deg
            e2 = self.e2.deg
            dx = (
                (a3 + e1) * np.cos(x[1] * np.pi / 180)
                + (a1 - e2) * np.sin(x[1] * np.pi / 180)
                + (b1 + c2) * np.sin(x[0] * np.pi / 180) * np.sin(x[1] * np.pi / 180)
                - (b2 + c1) * np.cos(x[0] * np.pi / 180) * np.sin(x[1] * np.pi / 180)
                + c1 * np.sin(x[0] * np.pi / 180) * np.cos(x[0] * np.pi / 180)
                + c2 * np.cos(x[0] * np.pi / 180) * np.cos(x[1] * np.pi / 180)
                + a2
                + d1
            )

            dy = (
                e2 * np.cos(x[1] * np.pi / 180)
                + e1 * np.sin(x[1] * np.pi / 180)
                + b1 * np.cos(x[0] * np.pi / 180)
                + b2 * np.sin(x[0] * np.pi / 180)
                + c1 * np.cos(x[0] * np.pi / 180) * np.cos(x[1] * np.pi / 180)
                + c1 * np.sin(x[0] * np.pi / 180) * np.sin(x[1] * np.pi / 180)
                - c2 * np.sin(x[0] * np.pi / 180) * np.cos(x[1] * np.pi / 180)
                + c2 * np.cos(x[0] * np.pi / 180) * np.sin(x[1] * np.pi / 180)
                + g1 * x[1]
                + b3
                + d2
            )
            print(dx, dy)

            f = np.zeros(2, dtype=float)

            f[0] = (x[0] + (dx / np.cos(x[1] * np.pi / 180)) - Az0) * (
                1
                + (1 / np.cos(x[1] * np.pi / 180))
                * (
                    (b1 + c2) * np.cos(x[0] * np.pi / 180) * np.sin(x[1] * np.pi / 180)
                    + (b2 + c1)
                    * np.sin(x[0] * np.pi / 180)
                    * np.sin(x[1] * np.pi / 180)
                    + c1 * np.cos(x[0] * np.pi / 180) * np.cos(x[1] * np.pi / 180)
                    - c2 * np.sin(x[0] * np.pi / 180) * np.cos(x[1] * np.pi / 180)
                )
            ) + (x[1] + dy - El0) * (
                -b1 * np.sin(x[0] * np.pi / 180)
                + b2 * np.cos(x[0] * np.pi / 180)
                - c1 * np.sin(x[0] * np.pi / 180) * np.cos(x[1] * np.pi / 180)
                + c1 * np.cos(x[0] * np.pi / 180) * np.sin(x[1] * np.pi / 180)
                - c2 * np.cos(x[0] * np.pi / 180) * np.cos(x[1] * np.pi / 180)
                - c2 * np.sin(x[0] * np.pi / 180) * np.sin(x[1] * np.pi / 180)
            )
            f[1] = (x[0] + (dx / np.cos(x[1] * np.pi / 180)) - Az0) * (
                np.tan(x[1] * np.pi / 180) * dx
                + (1 / np.cos(x[1] * np.pi / 180))
                * (
                    -(a3 + e1) * np.sin(x[1] * np.pi / 180)
                    + (a1 - e2) * np.cos(x[1] * np.pi / 180)
                    + (b1 + c2)
                    * np.sin(x[0] * np.pi / 180)
                    * np.cos(x[1] * np.pi / 180)
                    - (b2 + c1)
                    * np.cos(x[0] * np.pi / 180)
                    * np.cos(x[1] * np.pi / 180)
                    - c1 * np.sin(x[0] * np.pi / 180) * np.sin(x[1] * np.pi / 180)
                    - c2 * np.cos(x[0] * np.pi / 180) * np.sin(x[1] * np.pi / 180)
                )
            ) + (x[1] + dy - El0) * (
                -e2 * np.sin(x[1] * np.pi / 180)
                + e1 * np.cos(x[1] * np.pi / 180)
                - c1 * np.sin(x[0] * np.pi / 180) * np.sin(x[1] * np.pi / 180)
                + c1 * np.sin(x[0] * np.pi / 180) * np.cos(x[1] * np.pi / 180)
                + c2 * np.sin(x[0] * np.pi / 180) * np.sin(x[1] * np.pi / 180)
                + c2 * np.cos(x[0] * np.pi / 180) * np.cos(x[1] * np.pi / 180)
                + g1
                + 1
            )
            return f

        dAz, dEl = self.offset(az, el)
        az0 = az - dAz
        el0 = el - dEl
        x0 = np.array([az0.deg, el0.deg])

        ans = scipy.optimize.root(res, x0, method="hybr", tol=1e-13)
        az, el = ans.x

        return az * u.deg, el * u.deg

    def fit(self, *args, **kwargs):
        raise NotImplementedError("Fitting is not implemented for this model.")
