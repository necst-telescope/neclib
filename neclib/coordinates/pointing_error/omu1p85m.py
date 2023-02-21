from typing import Tuple

import astropy.units as u
import numpy as np

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

    def fit(self, *args, **kwargs):
        raise NotImplementedError("Fitting is not implemented for this model.")
