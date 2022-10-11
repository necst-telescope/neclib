__all__ = ["DriveLimitChecker"]

from typing import Optional

import astropy.units as u
import numpy as np

from .. import get_logger, utils
from ..typing import QuantityValue, Unit


class DriveLimitChecker:
    """Find optimum and safe angle to drive to.

    The optimization includes:

    1. Apply drive range constraint
    2. Avoid direction unwrapping (360deg drive) during observation
    3. Over-180deg drive

    Parameters
    ----------
    limit
        Drive range limit, the optimization result never go out of this range.
    preferred_limit
        Drive range limit, which can be violated to continue observation or no other
        choice found.
    unit
        Angular unit in which the parameters are given.
    max_observation_size
        If separation between current and target coordinates is smaller than this value,
        direction unwrapping won't occur, possibly violating ``preferred_limit``, to
        not interrupt observation.

    Examples
    --------
    >>> checker = neclib.coordinates.DriveLimitChecker(
    ...     [-260 << u.deg, 260 << u.deg], [-250 << u.deg, 250 << u.deg]
    ... )
    >>> checker.optimize(current=-200 << u.deg, target=170 << u.deg)
    <Quantity -190. deg>

    """

    def __init__(
        self,
        limit: utils.ValueRange[QuantityValue],
        preferred_limit: utils.ValueRange[QuantityValue] = None,
        *,
        unit: Unit = None,
        max_observation_size: QuantityValue = 5 << u.deg,
    ) -> None:
        self.logger = get_logger(self.__class__.__name__)

        limit = utils.get_quantity(*limit, unit=unit)
        if preferred_limit is None:
            preferred_limit = limit
        preferred_limit = utils.get_quantity(*preferred_limit, unit=unit)
        max_observation_size = utils.get_quantity(max_observation_size, unit=unit)

        self.limit = utils.ValueRange(*limit)
        self.preferred_limit = utils.ValueRange(*preferred_limit)
        self.max_observation_size = max_observation_size

        # This script doesn't silently swap the lower and upper bounds for `limit` and
        # `preferred_limit`, since the ambiguity can cause destructive result, i.e.
        # [270, 90]deg can mean [-90, 90]deg, which is opposite to [90, 270]deg.

    def optimize(
        self, current: QuantityValue, target: QuantityValue, unit: Unit = None
    ) -> u.Quantity:
        """Optimize the coordinate to command.

        Parameters
        ----------
        current
            Current coordinate, scalar or n-d array of shape [..., N].
        target
            Target coordinate to be optimized, scalar or n-d array of shape [..., N] or
            [..., N, T], where T is time series length.
        unit
            Angular unit in which the ``current`` and ``target`` are given.

        """
        current, target = utils.get_quantity(current, target, unit=unit)
        target_shape = target.shape

        if current.shape == target_shape:
            target = target[..., None]  # Add time series dimension
        elif current.shape == target_shape[:-1]:
            pass
        else:
            shape = ",".join(current.shape)
            raise ValueError(
                f"Target shape should be ({shape}) or ({shape}, T), got {target_shape}"
            )

        _360deg = 360 << u.deg
        min_candidate = target - _360deg * ((target - self.limit.lower) // _360deg)

        optimum = []
        for i in range(target.shape[-1]):
            _selected = self._select_onestep(current, min_candidate[..., i])
            optimum.append(_selected)
            current = _selected

        result = u.Quantity(optimum).reshape(target_shape)
        return self._validate(result, target)

    def _select_onestep(
        self, current: u.Quantity, min_candidate: u.Quantity
    ) -> u.Quantity:
        """Select the optimum from candidates, one-step in time series."""
        if current.shape != min_candidate.shape:
            raise ValueError(
                "`current` and `min_candidate` must have same shape, got"
                f"'{current.shape}' and '{min_candidate.shape}'"
            )

        def __select(mc: u.Quantity) -> u.Quantity:
            nonlocal current
            candidates = u.Quantity(
                list(utils.frange(mc, self.limit.upper, 360 << u.deg))
            )
            current = self._select(current, candidates)
            return current

        optimum = u.Quantity([__select(mc) for mc in min_candidate.flat])
        return optimum.reshape(min_candidate.shape)

    def _select(self, current: u.Quantity, candidates: u.Quantity) -> u.Quantity:
        if candidates.ndim != 1:
            raise ValueError(
                f"Candidates should be 1-d array, got array of shape {current.shape}"
            )
        if candidates.size == 0:
            return float("nan") << u.deg
        if candidates.size == 1:
            return candidates.reshape(())

        distance = abs(candidates - current)
        sorted_indices_by_distance = distance.argsort()
        for idx in sorted_indices_by_distance:
            if distance[idx] < self.max_observation_size:
                return candidates[idx]
            if candidates[idx] in self.preferred_limit:
                return candidates[idx]

    def _validate(self, result: u.Quantity, target: u.Quantity) -> Optional[u.Quantity]:
        is_not_finite = ~np.isfinite(result)
        if is_not_finite.any():
            self.logger.warning(
                f"{is_not_finite.sum()} of instructed coordinates are out of drive "
                f"range {self.limit} : {target[is_not_finite]}"
            )
            return

        if self.preferred_limit.contain_all(result):
            return result
        self.logger.warning("Command position nears drive range limit.")
        return result
