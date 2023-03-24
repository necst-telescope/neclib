from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Tuple, Union

import astropy.units as u

from ...core.types import CoordFrameType, DimensionLess, UnitType
from .path_base import ControlContext, Index, Path

if TYPE_CHECKING:
    from ..convert import CoordCalculator

T = Union[DimensionLess, u.Quantity]


class Track(Path):

    tight = True
    infinite = True
    waypoint = False

    def __init__(
        self,
        calc: CoordCalculator,
        *target: Union[str, DimensionLess, u.Quantity, CoordFrameType],
        unit: Optional[UnitType] = None,
        offset: Optional[Tuple[T, T, CoordFrameType]] = None,
        **ctx_kw: Any,
    ) -> None:
        super().__init__(calc, *target, unit=unit)

        self._offset = (
            None
            if offset is None
            else calc.coordinate_delta(
                d_lon=offset[0], d_lat=offset[1], frame=offset[2], unit=unit
            )
        )
        self._ctx_kw = ctx_kw

        require_unit = (
            (offset is not None) and (not isinstance(offset[0], u.Quantity))
        ) or (not isinstance(target[0], (str, u.Quantity)))
        if (unit is None) and require_unit:
            raise ValueError(
                "`unit` is required when `target` or `offset` is given as float value."
            )
        self._unit = unit

    @property
    def n_cmd(self) -> Union[int, float]:
        return self._calc.command_freq * self._calc.command_group_duration_sec

    @property
    def lonlat_func(self) -> Callable[[Index], Tuple[T, T]]:
        def _lonlat_func(idx: Index) -> Tuple[T, T]:
            target = (
                self._target.realize(time=idx.time)  # type: ignore
                if hasattr(self._target, "realize")
                else self._target
            )
            target = target.replicate(time=idx.time)  # type: ignore
            offset_applied = (
                target.cartesian_offset_by(self._offset) if self._offset else target
            )
            return offset_applied.lon, offset_applied.lat

        return _lonlat_func

    @property
    def arguments(self) -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        ctx_kw = dict(
            tight=self.tight,
            infinite=self.infinite,
            waypoint=self.waypoint,
            duration=self._calc.command_group_duration_sec,
        )
        ctx_kw.update(self._ctx_kw)

        kwargs: Dict[str, Any] = dict(
            n_cmd=self.n_cmd, context=ControlContext(**ctx_kw)
        )
        if self._unit is not None:
            kwargs.update(unit=self._unit)

        return (self.lonlat_func, self.target_frame), {
            "n_cmd": self.n_cmd,
            "context": ControlContext(**ctx_kw),
            "unit": self._unit,
        }
