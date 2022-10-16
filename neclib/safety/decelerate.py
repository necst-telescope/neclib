"""Additionally restrict the maximum drive speed near drive range limits.

If you understand the junior-high physics, you know the algorithm.

"""

import astropy.units as u

from ..typing import QuantityValue, Unit
from .. import utils


class Decelerate:
    def __init__(
        self,
        limit: utils.ValueRange[u.Quantity],
        max_acceleration: u.Quantity,
    ) -> None:
        self.limit = limit
        self.max_acceleration = max_acceleration

    def __call__(
        self,
        encoder_reading: QuantityValue,
        velocity: QuantityValue,
        angle_unit: Unit = None,
    ) -> u.Quantity:
        velocity = utils.get_quantity(
            velocity, unit=(None if angle_unit is None else f"{angle_unit}/s")
        )
        encoder_reading = utils.get_quantity(encoder_reading, unit=angle_unit)

        if encoder_reading not in self.limit:
            return 0 << velocity.unit

        position_relative_to_limits = (limit - encoder_reading for limit in self.limit)
        max_velocity_squared = (
            2 * self.max_acceleration * rel for rel in position_relative_to_limits
        )
        max_velocity = (
            v**0.5 if v.value == 0 else v / (abs(v) ** 0.5)
            for v in max_velocity_squared
        )

        return utils.clip(velocity, *max_velocity)
