from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Tuple, Union

import astropy.units as u
from astropy.coordinates import SkyCoord

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
        super().__init__(calc)

        self._offset = offset
        self._ctx_kw = ctx_kw

        if (len(target) == 1) and isinstance(target[0], str):
            _target = target[0]
        elif len(target) == 3:
            lon, lat, frame = target
            _target = self._calc.create_skycoord(lon, lat, frame=frame, unit=unit)
        else:
            raise TypeError(
                "Invalid number of positional arguments: expected 1 "
                "(target_name) or 3 (lon, lat, coordinate_frame), but got"
                f" {len(target)}"
            )
        self._target = _target

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
            if isinstance(self._target, str):
                _target = self._calc.get_body(self._target, idx.time)
            else:
                _target = self._target

            if self._offset is not None:
                offset_applied = self._calc.cartesian_offset_by(
                    _target, *self._offset, unit=self._unit, obstime=idx.time
                )
                return offset_applied.data.lon, offset_applied.data.lat  # type: ignore
            else:
                return _target.data.lon, _target.data.lat  # type: ignore

        return _lonlat_func

    @property
    def frame(self) -> CoordFrameType:
        if isinstance(self._target, SkyCoord):
            return self._target.frame
        else:
            return self._calc.get_body(self._target, time.time()).frame

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

        return (self.lonlat_func, self.frame), {
            "n_cmd": self.n_cmd,
            "context": ControlContext(**ctx_kw),
            "unit": self._unit,
        }
