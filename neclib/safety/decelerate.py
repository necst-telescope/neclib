r"""Additionally restrict the maximum drive speed near drive range limits.

If you understand the junior-high physics, you know the algorithm:

.. math::

   v &= \int a \ dt = a \int dt = at \qquad (v_0 = 0) \\
   x &= \int v \ dt = a \int t \ dt = \frac{a t^2}{2} \qquad (x_0 = 0) \\
   v(x) &= a \sqrt{\frac{2x}{a}} = \sqrt{2ax}

where :math:`x` is the distance between encoder reading and drive limits.

"""

from typing import Optional

import astropy.units as u

from ..core import ValueRange, get_quantity, math
from ..core.types import DimensionLess, Union, UnitType


class Decelerate:
    """Decelerate the telescope drive as it nears the drive range limits.

    Parameters
    ----------
    limit
        The range of encoder values that are considered the drive range limits.
    max_acceleration
        The maximum (absolute) acceleration of the telescope drive.

    Examples
    --------
    >>> limit = neclib.core.ValueRange(5 << u.deg, 355 << u.deg)
    >>> calculator = neclib.safety.Decelerate(limit, 1.0 << u.deg / u.s**2)
    >>> calculator(354.6 << u.deg, 1 << u.deg / u.s)
    <Quantity 0.89442719 deg / s>
    >>> calculator(354.6 << u.deg, -1 << u.deg / u.s)
    <Quantity -1. deg / s>

    """

    def __init__(
        self,
        limit: ValueRange[u.Quantity],  # type: ignore
        max_acceleration: u.Quantity,
    ) -> None:
        self.limit = limit
        self.max_acceleration = max_acceleration

    def __call__(
        self,
        encoder_reading: Union[DimensionLess, u.Quantity],
        velocity: Union[DimensionLess, u.Quantity],
        angle_unit: Optional[UnitType] = None,
    ) -> u.Quantity:
        velocity = get_quantity(
            velocity, unit=(None if angle_unit is None else f"{angle_unit}/s")
        )
        encoder_reading = get_quantity(encoder_reading, unit=angle_unit)

        if encoder_reading not in self.limit:
            return 0 << velocity.unit  # type: ignore

        position_relative_to_limits = (limit - encoder_reading for limit in self.limit)
        max_velocity_squared = (
            2 * self.max_acceleration * rel for rel in position_relative_to_limits
        )
        max_velocity = (
            v**0.5 if v.value == 0 else v / (abs(v) ** 0.5)  # type: ignore
            for v in max_velocity_squared
        )

        return math.clip(velocity, *max_velocity)  # type: ignore
