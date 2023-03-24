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
        self._offset = (
            None
            if offset is None
            else calc.coordinate_delta(
                d_lon=offset[0], d_lat=offset[1], frame=offset[2], unit=unit
            )
        )
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
        if self._offset is not None:
            return self._offset.frame
        return self._scan_frame

    @property
    def lonlat_func(self) -> Callable[[Index], Tuple[T, T]]:
        def _lonlat_func(idx: Index) -> Tuple[T, T]:
            if self._target is None:
                kw = dict(frame=self._scan_frame, unit=self._unit, time=idx.time)
                _start = self._calc.coordinate(
                    lon=self._start[0], lat=self._start[1], **kw
                )
                _stop = self._calc.coordinate(
                    lon=self._stop[0], lat=self._stop[1], **kw
                )
            else:
                _reference = (
                    self._target.realize(time=idx.time)  # type: ignore
                    if hasattr(self._target, "realize")
                    else self._target
                )
                _reference = _reference.replicate(time=idx.time)
                offset_to_start = self._calc.coordinate_delta(
                    d_lon=self._start[0], d_lat=self._start[1], frame=self._scan_frame
                )
                offset_to_stop = self._calc.coordinate_delta(
                    d_lon=self._stop[0], d_lat=self._stop[1], frame=self._scan_frame
                )
                _start = _reference.cartesian_offset_by(offset_to_start)
                _stop = _reference.cartesian_offset_by(offset_to_stop)

            start = (
                _start
                if self._offset is None
                else _start.cartesian_offset_by(self._offset)
            )
            stop = (
                _stop
                if self._offset is None
                else _stop.cartesian_offset_by(self._offset)
            )

            _ratio = idx.index / self.n_cmd  # type: ignore
            lon = start.lon * (1 - _ratio) + stop.lon * _ratio
            lat = start.lat * (1 - _ratio) + stop.lat * _ratio

            return lon, lat

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
                kw = dict(frame=self._scan_frame, unit=self._unit, time=idx.time)
                _start = self._calc.coordinate(
                    lon=margin_start[0], lat=margin_start[1], **kw
                )
                _stop = self._calc.coordinate(
                    lon=self._start[0], lat=self._start[1], **kw
                )
            else:
                kw = dict(obstime=idx.time, unit=self._unit)
                _reference = (
                    self._target.realize(time=idx.time)  # type: ignore
                    if hasattr(self._target, "realize")
                    else self._target
                )
                _reference = _reference.replicate(time=idx.time)
                offset_to_start = self._calc.coordinate_delta(
                    d_lon=margin_start[0], d_lat=margin_start[1], frame=self._scan_frame
                )
                offset_to_stop = self._calc.coordinate_delta(
                    d_lon=self._start[0], d_lat=self._start[1], frame=self._scan_frame
                )
                _start = _reference.cartesian_offset_by(offset_to_start)
                _stop = _reference.cartesian_offset_by(offset_to_stop)

            start = (
                _start
                if self._offset is None
                else _start.cartesian_offset_by(self._offset)
            )
            stop = (
                _stop
                if self._offset is None
                else _stop.cartesian_offset_by(self._offset)
            )

            _ratio = idx.index / self.n_cmd  # type: ignore
            lon = start.lon * (1 - _ratio**2) + stop.lon * _ratio**2
            lat = start.lat * (1 - _ratio**2) + stop.lat * _ratio**2

            return lon, lat

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
                kw = dict(frame=self._scan_frame, unit=self._unit, time=idx.time)
                _start = self._calc.coordinate(
                    lon=margin_start[0], lat=margin_start[1], **kw
                )
            else:
                kw = dict(obstime=idx.time, unit=self._unit)
                _reference = (
                    self._target.realize(time=idx.time)  # type: ignore
                    if hasattr(self._target, "realize")
                    else self._target
                )
                _reference = _reference.replicate(time=idx.time)
                offset = self._calc.coordinate_delta(
                    d_lon=margin_start[0], d_lat=margin_start[1], frame=self._scan_frame
                )
                _start = _reference.cartesian_offset_by(offset)

            start = (
                _start
                if self._offset is None
                else _start.cartesian_offset_by(self._offset)
            )
            lon = np.broadcast_to(start.lon, idx.time.shape)  # type: ignore
            lat = np.broadcast_to(start.lat, idx.time.shape)  # type: ignore

            return lon, lat

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
