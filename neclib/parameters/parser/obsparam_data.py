"""Storage for observation parameter."""

__all__ = ["ObsParamData"]

from typing import Any, Dict, Hashable

from astropy.coordinates import Angle
from astropy.units import Quantity
from tomlkit.toml_file import TOMLFile

from ...utils import ParameterMapping
from ...typing import PathLike


class ObsParamData(ParameterMapping):
    """Parse observation spec as Quantity.

    Parameters named uppercase (``A-Z0-9_``) will be parsed as it is, lowercase
    (``a-z0-9_``) will be parsed as ``Quantity``, mixed case (``[A-Z]+[a-z]+0-9_``) will
    be parsed as ``Angle``.

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
        >>> params = neclib.parameters.ObsParamData.from_file("path/to/spec.obs.toml")
        >>> params
        ObsParams({'OBSERVER': 'amigos', 'OBJECT': 'OriKL', ...})
        >>> params.OBSERVER
        'amigos'
        >>> params["OBJECT"]
        'OriKL'

        """
        _params = TOMLFile(path).read()
        params = {}
        _ = [params.update(subdict) for subdict in _params.values()]
        return cls(**params)

    @staticmethod
    def _make_quantity(parameters: Dict[Hashable, Any]) -> Dict[Hashable, Any]:
        parsed = {}
        for name, value in parameters.items():
            if value == {}:  # Empty value
                pass
            elif name.isupper():
                parsed[name] = value
            elif name.islower():
                parsed[name] = Quantity(value)
            else:
                parsed[name] = Angle(value)
        return parsed
