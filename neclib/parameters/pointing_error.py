"""Pointing error correction.

The telescope pointing is critically important in performing accurate and uniform
observation. This module employs following pointing model:

"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, fields
from typing import Optional, Tuple, final

import astropy.units as u
import numpy as np
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
        \Delta Az =& \Delta x / \cos ( El ) \\
        \Delta y =& b_1 \cos ( Az ) \\
        &+ b_2 \sin ( Az ) \\
        &+ b_3 \\
        &+ g_1 El \\
        &+ c_1 \cos ( Az - El ) \\
        &- c_2 \sin ( Az - El ) \\
        &+ d_2 \\
        &+ e_1 \sin ( El ) \\
        &+ e_2 \cos ( El ) \\
        \Delta El =& \Delta y

    """

    a1: Angle = 0 << u.deg
    a2: Angle = 0 << u.deg
    a3: Angle = 0 << u.deg
    b1: Angle = 0 << u.deg
    b2: Angle = 0 << u.deg
    b3: Angle = 0 << u.deg
    g1: float = 0
    c1: Angle = 0 << u.deg
    c2: Angle = 0 << u.deg
    d1: Angle = 0 << u.deg
    d2: Angle = 0 << u.deg
    e1: Angle = 0 << u.deg
    e2: Angle = 0 << u.deg

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
        return dAz, dEl

    def fit(self, *args, **kwargs):
        raise NotImplementedError("Fitting is not implemented for this model.")
