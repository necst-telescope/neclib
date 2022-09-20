__all__ = ["DriveLimitChecker"]

from typing import List, Tuple

import astropy.units as u

from neclib import logger
from ..typing import QuantityValue, Unit
from .. import utils


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
        limit: Tuple[QuantityValue, QuantityValue],
        preferred_limit: Tuple[QuantityValue, QuantityValue] = None,
        *,
        unit: Unit = None,
        max_observation_size: QuantityValue = 5 << u.deg,
    ) -> None:
        self.limit = utils.get_quantity(*limit, unit=unit)
        self.max_observation_size = utils.get_quantity(max_observation_size, unit=unit)
        if preferred_limit is None:
            self.preferred_limit = self.limit
        else:
            self.preferred_limit = utils.get_quantity(*preferred_limit, unit=unit)

        _limit_ascending = self.limit[0] < self.limit[1]
        _preferred_limit_ascending = self.preferred_limit[0] < self.preferred_limit[1]
        if (not _limit_ascending) or (not _preferred_limit_ascending):
            # Silently swapping the values could cause destructive result, i.e.
            # [270deg, 90deg] can mean [-90deg, 90deg], which is opposite to
            # [90deg, 270deg].
            raise ValueError("Limits should be given in ascending order.")

    def _get_candidates(self, target: u.Quantity) -> List[u.Quantity]:
        # NOTE: Author has made no effort making this algorithm readable, but the logic
        # isn't so complicated.
        _360deg = 360 << u.deg
        min_target_candidate = target - _360deg * ((target - self.limit[0]) // _360deg)

        target_candidates = [
            angle
            for angle in utils.frange(min_target_candidate, self.limit[1], _360deg)
        ]
        return target_candidates

    def _select(self, current: u.Quantity, candidates: List[u.Quantity]) -> u.Quantity:
        if len(candidates) < 1:
            return
        if len(candidates) == 1:
            return candidates[0]

        ordered_by_distance = sorted(
            [(t, abs(t - current)) for t in candidates], key=lambda x: x[1]
        )
        for target, distance in ordered_by_distance:
            if distance < self.max_observation_size:
                return target
            if self.preferred_limit[0] < target < self.preferred_limit[1]:
                return target

    def optimize(
        self,
        current: QuantityValue,
        target: QuantityValue,
        unit: Unit = None,
    ) -> u.Quantity:
        """Optimize the coordinate to command.

        Parameters
        ----------
        current
            Current coordinate.
        target
            Target coordinate, to be optimized.
        unit
            Angular unit in which the ``current`` and ``target`` are given.

        """
        current, target = utils.get_quantity(current, target, unit=unit)

        def _optimize(_target):
            target_candidates = self._get_candidates(_target)
            return self._select(current, target_candidates)

        optimized = (
            [_optimize(t) for t in target] if target.shape else _optimize(target)
        )
        if (optimized is None) or (isinstance(optimized, list) and (None in optimized)):
            logger.warning(
                f"Instructed coordinate {target} out of drive range {self.limit}"
            )
        self._warn_unpreferred_result(optimized)
        return optimized

    def _warn_unpreferred_result(self, result: u.Quantity) -> None:
        def condition(v):
            lower = self.limit[0] < v < self.preferred_limit[0]
            upper = self.limit[1] > v > self.preferred_limit[1]
            return lower or upper

        unpreferred = (
            any(condition(v) for v in result)
            if isinstance(result, list)
            else condition(result)
        )
        if unpreferred:
            logger.warning("Command position is near drive range limit.")
