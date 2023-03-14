from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Tuple, Union

import astropy.units as u
import numpy as np

from ...core.normalization import get_quantity
from ...core.types import CoordFrameType, DimensionLess, UnitType
from .path_base import ControlContext, Index, Path

if TYPE_CHECKING:
    from ..convert import CoordCalculator

T = Union[DimensionLess, u.Quantity]


class Linear(Path):

    tight = True
    infinite = False
    waypoint = False

    def __init__(
        self,
        calc: CoordCalculator,
        *target: Union[str, DimensionLess, u.Quantity, CoordFrameType],
        unit: Optional[UnitType] = None,
        start: Tuple[T, T],
        stop: Tuple[T, T],
        scan_frame: CoordFrameType,
        speed: T,
        offset: Optional[Tuple[T, T, CoordFrameType]] = None,
        margin: Optional[T] = None,
        **ctx_kw: Any,
    ) -> None:
        super().__init__(calc, *target, unit=unit)

        self._start = get_quantity(start, unit=unit)  # type: ignore
        self._stop = get_quantity(stop, unit=unit)  # type: ignore
        self._scan_frame = scan_frame
        self._speed = get_quantity(speed, unit=f"{unit}/s")
        self._offset = offset
        self._ctx_kw = ctx_kw

        require_unit = (
            ((offset is not None) and (not isinstance(offset[0], u.Quantity)))
            or ((len(target) > 0) and (not isinstance(target[0], u.Quantity)))
            or (not isinstance(start[0], u.Quantity))
            or (not isinstance(stop[0], u.Quantity))
        )
        if (unit is None) and require_unit:
            raise ValueError(
                "Unit must be specified if any of the following arguments are not "
                "quantities; `target`, `start`, `stop`, `offset`"
            )
        self._unit = unit

        if margin is None:
            raise NotImplementedError("Auto-margin is not implemented yet")
        self._margin = get_quantity(margin, unit=unit)

    @property
    def n_cmd(self) -> Union[int, float]:
        distance: u.Quantity = np.linalg.norm(
            np.asanyarray(self._start) - np.asanyarray(self._stop)  # type: ignore
        )
        duration_sec = (distance / self._speed).to_value("s")
        return float(duration_sec * self._calc.command_freq)  # type: ignore

    @property
    def target_frame(self) -> CoordFrameType:
        if self._target is None:
            return self._scan_frame

        return super().target_frame  # type: ignore

    @property
    def lonlat_func(self) -> Callable[[Index], Tuple[T, T]]:
        def _lonlat_func(idx: Index) -> Tuple[T, T]:
            if self._target is None:
                kw = dict(frame=self._scan_frame, unit=self._unit)
                _start = self._calc.create_skycoord(*self._start, **kw)
                _stop = self._calc.create_skycoord(*self._stop, **kw)
            elif isinstance(self._target, str):
                kw = dict(obstime=idx.time, unit=self._unit)
                _reference = self._calc.get_body(self._target, idx.time)
                _start = self._calc.cartesian_offset_by(
                    _reference, self._start[0], self._start[1], self._scan_frame, **kw
                )
                _stop = self._calc.cartesian_offset_by(
                    _reference, self._stop[0], self._stop[1], self._scan_frame, **kw
                )
            else:
                kw = dict(obstime=idx.time, unit=self._unit)
                _start = self._calc.cartesian_offset_by(
                    self._target, self._start[0], self._start[1], self._scan_frame, **kw
                )
                _stop = self._calc.cartesian_offset_by(
                    self._target, self._stop[0], self._stop[1], self._scan_frame, **kw
                )

            start, stop = self.apply_offset(
                _start, _stop, offset=self._offset, obstime=idx.time, unit=self._unit
            )

            _ratio = idx.index / self.n_cmd  # type: ignore
            pts = start.data * (1 - _ratio) + stop.data * _ratio

            return pts.lon, pts.lat

        return _lonlat_func

    @property
    def arguments(self) -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        ctx_kw = dict(
            tight=self.tight,
            infinite=self.infinite,
            waypoint=self.waypoint,
            duration=self.n_cmd / self._calc.command_freq,
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


class Accelerate(Linear):

    tight = False
    infinite = False
    waypoint = False

    @property
    def n_cmd(self) -> Union[int, float]:
        a = (self._speed**2) / (2 * self._margin)
        duration = ((2 * self._margin) / a) ** (1 / 2)
        return float(duration.to_value("s") * self._calc.command_freq)  # type: ignore

    @property
    def lonlat_func(self) -> Callable[[Index], Tuple[T, T]]:
        scan_vector: u.Quantity = self._stop - self._start  # type: ignore
        unit_scan_vector = scan_vector / np.linalg.norm(scan_vector) * scan_vector.unit
        margin_start = self._start - unit_scan_vector * self._margin.to_value(
            unit_scan_vector.unit
        )

        def _lonlat_func(idx: Index) -> Tuple[T, T]:
            if self._target is None:
                kw = dict(frame=self._scan_frame, unit=self._unit)
                _start = self._calc.create_skycoord(*margin_start, **kw)
                _stop = self._calc.create_skycoord(*self._start, **kw)
            elif isinstance(self._target, str):
                kw = dict(obstime=idx.time, unit=self._unit)
                _reference = self._calc.get_body(self._target, idx.time)
                _start = self._calc.cartesian_offset_by(
                    _reference, margin_start[0], margin_start[1], self._scan_frame, **kw
                )
                _stop = self._calc.cartesian_offset_by(
                    _reference, self._start[0], self._start[1], self._scan_frame, **kw
                )
            else:
                kw = dict(obstime=idx.time, unit=self._unit)
                _start = self._calc.cartesian_offset_by(
                    self._target,
                    margin_start[0],
                    margin_start[1],
                    self._scan_frame,
                    **kw,
                )
                _stop = self._calc.cartesian_offset_by(
                    self._target, self._start[0], self._start[1], self._scan_frame, **kw
                )

            start, stop = self.apply_offset(
                _start, _stop, offset=self._offset, obstime=idx.time, unit=self._unit
            )

            _ratio = idx.index / self.n_cmd  # type: ignore
            pts = start.data * (1 - _ratio**2) + stop.data * _ratio**2

            return pts.lon, pts.lat

        return _lonlat_func

    @property
    def arguments(self) -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        ctx_kw = dict(
            tight=self.tight,
            infinite=self.infinite,
            waypoint=self.waypoint,
            duration=self.n_cmd / self._calc.command_freq,
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


class Standby(Linear):

    tight = True
    infinite = True
    waypoint = True

    @property
    def n_cmd(self) -> Union[int, float]:
        return self._calc.command_freq * self._calc.command_group_duration_sec

    @property
    def lonlat_func(self) -> Callable[[Index], Tuple[T, T]]:
        scan_vector: u.Quantity = self._stop - self._start  # type: ignore

        unit_scan_vector = scan_vector / np.linalg.norm(scan_vector) * scan_vector.unit
        margin_start = self._start - unit_scan_vector * self._margin.to_value(
            unit_scan_vector.unit
        )

        def _lonlat_func(idx: Index) -> Tuple[T, T]:
            if self._target is None:
                kw = dict(frame=self._scan_frame, unit=self._unit)
                _start = self._calc.create_skycoord(*margin_start, **kw)
            elif isinstance(self._target, str):
                kw = dict(obstime=idx.time, unit=self._unit)
                _reference = self._calc.get_body(self._target, idx.time)
                _start = self._calc.cartesian_offset_by(
                    _reference, margin_start[0], margin_start[1], self._scan_frame, **kw
                )
            else:
                kw = dict(obstime=idx.time, unit=self._unit)
                _start = self._calc.cartesian_offset_by(
                    self._target,
                    margin_start[0],
                    margin_start[1],
                    self._scan_frame,
                    **kw,
                )

            start = self.apply_offset(
                _start, offset=self._offset, obstime=idx.time, unit=self._unit
            )
            pts = np.broadcast_to(start.data, idx.time.shape)  # type: ignore

            return pts.lon, pts.lat

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
