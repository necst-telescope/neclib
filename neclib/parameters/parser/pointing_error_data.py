"""Storage for pointing error parameter."""

__all__ = ["PointingErrorData"]

from pathlib import Path
from typing import Any, Dict, Hashable

import astropy.units as u
from astropy.coordinates import Angle
from tomlkit.toml_file import TOMLFile

from ...typing import PathLike
from ...utils import ParameterMapping


class PointingErrorData(ParameterMapping):
    """Parse pointing error parameter as Quantity.

    Attributes
    ----------
    dAz: Angle
        Azimuth (not X) offset of encoder reading.
    de: Angle
        X collimation error.
    chi_Az: Angle
        Magnitude of tilt of azimuth axis.
    omega_Az: Angle
        Phase (azimuth direction) of tilt of azimuth axis.
    eps: Angle
        Skew angle (lack of orthogonality) between azimuth and elevation axes.
    chi2_Az: Angle
        Same as chi, but the period is 180deg in azimuth axis (harmonic component).
    omega2_Az: Angle
        Same as omega, but the period is 180deg in azimuth (harmonic component).
    chi_El: Angle
        Amplitude of tilt of azimuth axis (same as chi_Az).
    omega_El: Angle
        Phase (azimuth direction) of tilt of azimuth axis (same as omega_Az).
    chi2_El: Angle
        Same as chi, but the period is 180deg in azimuth axis (harmonic component,
        same as chi2_Az).
    omega2_El: Angle
        Same as omega, but the period is 180deg in azimuth (harmonic component, same
        as omega2_Az).
    g: float
        First order gravitational deflection coefficient.
    gg: float
        Second order gravitational deflection coefficient.
    ggg: float
        Third order gravitational deflection coefficient.
    gggg: float
        Fourth order gravitational deflection coefficient.
    dEl: Angle
        Elevation offset of encoder reading.
    de_radio: Angle
        Constant X (not azimuth) offset between optical and radio beam.
    del_radio: Angle
        Constant elevation offset between optical and radio beam.
    cor_v: Angle
        Amplitude of collimation error.
    cor_p: Angle
        Phase of collimation error, negative of elevation where the elevation
        component of collimation error is zero.
    g_radio: float
        First order gravitational deflection coefficient.
    gg_radio: float
        Second order gravitational deflection coefficient.
    ggg_radio: float
        Third order gravitational deflection coefficient.
    gggg_radio: float
        Fourth order gravitational deflection coefficient.

    """

    def __init__(self, **kwargs) -> None:
        kwargs = self._make_quantity(kwargs)
        super().__init__(**kwargs)

    @classmethod
    def from_file(cls, path: PathLike):
        """Parse TOML file.

        Parameters
        ----------
        path
            Path to parameter file.

        Notes
        -----
        Bare keys or nested tables are not allowed. Valid parameters are those declared
        in the following format. The table structure will be flattened, so the
        ``parameter kind`` won't be preserved.

        .. code-block:: toml

           [parameter kind]
           name = value

        Examples
        --------
        >>> params = neclib.parameters.PointingErrorData.from_file("path/to/error_param.toml")
        >>> params
        ObsParams({'dAz': <Quantity 5300. arcsec>, 'de': <Quantity 380. arcsec>, ...})
        >>> params.dAz
        <Quantity 5300. arcsec>
        >>> params["de"]
        <Quantity 380. arcsec>

        """  # noqa: E501
        _params = TOMLFile(path).read()
        params = {}
        _ = [params.update(subdict) for subdict in _params.values()]
        return cls(**params)

    @classmethod
    def from_text_file(cls, path: PathLike):
        """Parse legacy style pointing error parameter file.

        Parameters
        ----------
        path
            Path to parameter file.

        Examples
        --------
        >>> params = neclib.parameters.PointingErrorData.from_text_file("path/to/error_param.txt")
        >>> params
        ObsParams({'dAz': <Quantity 5300. arcsec>, 'de': <Quantity 380. arcsec>, ...})
        >>> params.dAz
        <Quantity 5300. arcsec>
        >>> params["de"]
        <Quantity 380. arcsec>

        """  # noqa: E501
        lines = Path(path).read_text().split("\n")
        filled_lines = [line for line in lines if line != ""]
        parameter_units: Dict[str, str] = [
            ("dAz", "arcsec"),
            ("de", "arcsec"),
            ("chi_Az", "arcsec"),
            ("omega_Az", "deg"),
            ("eps", "arcsec"),
            ("chi2_Az", "arcsec"),
            ("omega2_Az", "deg"),
            ("chi_El", "arcsec"),
            ("omega_El", "deg"),
            ("chi2_El", "arcsec"),
            ("omega2_El", "deg"),
            ("g", ""),
            ("gg", ""),
            ("ggg", ""),
            ("gggg", ""),
            ("dEl", "arcsec"),
            ("de_radio", "arcsec"),
            ("del_radio", "arcsec"),
            ("cor_v", "arcsec"),
            ("cor_p", "deg"),
            ("g_radio", ""),
            ("gg_radio", ""),
            ("ggg_radio", ""),
            ("gggg_radio", ""),
        ]
        parameters = {
            name: value + unit
            for value, (name, unit) in zip(filled_lines, parameter_units)
        }
        return cls(**parameters)

    @staticmethod
    def _make_quantity(parameters: Dict[Hashable, Any]) -> Dict[Hashable, Any]:
        parsed = {}
        for name, value in parameters.items():
            if value == {}:  # Empty value
                pass
            else:
                try:
                    parsed[name] = Angle(value)
                except (u.UnitsError, u.UnitTypeError):
                    parsed[name] = float(value)
        return parsed
