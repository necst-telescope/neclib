from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

import astropy.units as u
import numpy as np

from ...core import config, get_logger
from ...core.normalization import get_quantity
from ...core.types import CoordFrameType, DimensionLess, UnitType
from .linear import Linear, Standby
from .path_base import ControlContext, Index, Path

if TYPE_CHECKING:
    from ..convert import CoordCalculator

T = Union[DimensionLess, u.Quantity]


logger = get_logger(__name__, throttle_duration_sec=10)


@dataclass(frozen=True)
class ScanBlockKinematicLimits:
    max_speed: u.Quantity
    max_acceleration: u.Quantity
    max_jerk: Optional[u.Quantity] = None


def _scalar_limit(value: Any, *, unit: str) -> u.Quantity:
    if hasattr(value, "az") and hasattr(value, "el"):
        az = get_quantity(value.az, unit=unit)
        el = get_quantity(value.el, unit=unit)
        return az if az <= el else el
    return get_quantity(value, unit=unit)


def _config_float(name: str, default: float) -> float:
    try:
        value = getattr(config, name)
    except AttributeError:
        return float(default)
    try:
        if hasattr(value, "to_value"):
            return float(value.to_value(""))
    except Exception:
        pass
    try:
        return float(value)
    except Exception:
        return float(default)



def _provisional_jerk_limit(max_acceleration: u.Quantity) -> u.Quantity:
    command_frequency = _config_float("antenna_command_frequency", 50.0)
    if not np.isfinite(command_frequency) or (command_frequency <= 0.0):
        command_frequency = 50.0
    ramp_cycles = 5.0
    min_ramp_sec = 0.1
    ramp_sec = max(min_ramp_sec, ramp_cycles / command_frequency)
    return (max_acceleration / (ramp_sec * u.s)).to("deg/s^3")



def conservative_antenna_kinematic_limits(
    *,
    speed_headroom: float = 1.0,
    acceleration_headroom: float = 1.0,
    jerk_headroom: float = 1.0,
) -> ScanBlockKinematicLimits:
    max_speed = _scalar_limit(config.antenna_max_speed, unit="deg/s") * float(speed_headroom)
    max_acceleration = _scalar_limit(
        config.antenna_max_acceleration, unit="deg/s^2"
    ) * float(acceleration_headroom)

    jerk_source = None
    if hasattr(config, "antenna_max_jerk"):
        jerk_source = getattr(config, "antenna_max_jerk")
    elif hasattr(config, "antenna_max_jerk_az") and hasattr(config, "antenna_max_jerk_el"):
        jerk_source = type("AxisLimit", (), {
            "az": getattr(config, "antenna_max_jerk_az"),
            "el": getattr(config, "antenna_max_jerk_el"),
        })()
    max_jerk = None
    if jerk_source is not None:
        max_jerk = _scalar_limit(jerk_source, unit="deg/s^3") * float(jerk_headroom)
    else:
        max_jerk = _provisional_jerk_limit(max_acceleration) * float(jerk_headroom)

    return ScanBlockKinematicLimits(
        max_speed=max_speed,
        max_acceleration=max_acceleration,
        max_jerk=max_jerk,
    )


def _dimensionless_value(value: Any) -> float:
    if hasattr(value, "to_value"):
        try:
            return float(value.to_value(u.dimensionless_unscaled))
        except Exception:
            try:
                return float(value.to_value(""))
            except Exception:
                pass
    return float(np.asarray(value, dtype=float))


def _within_limit(value: u.Quantity, limit: Optional[u.Quantity], *, rtol: float = 1e-9) -> Optional[bool]:
    if limit is None:
        return None
    return _dimensionless_value(value / limit) <= (1.0 + float(rtol))


def _curve_control_points(
    start: Tuple[T, T],
    stop: Tuple[T, T],
    entry_direction: Tuple[T, T],
    exit_direction: Tuple[T, T],
    turn_radius_hint: Optional[T] = None,
    *,
    unit: Optional[UnitType] = None,
) -> Tuple[u.Quantity, u.Quantity, u.Quantity, u.Quantity]:
    p0 = get_quantity(start, unit=unit)  # type: ignore[arg-type]
    p3 = get_quantity(stop, unit=unit)  # type: ignore[arg-type]
    chord = p3 - p0  # type: ignore[operator]
    chord_len = np.linalg.norm(chord)
    if chord_len.to_value(chord.unit) == 0:
        return p0, p0, p3, p3

    entry = get_quantity(entry_direction, unit=unit)  # type: ignore[arg-type]
    entry_norm = np.linalg.norm(entry)
    if entry_norm.to_value(entry.unit) == 0:
        raise ValueError("Zero-length entry_direction is not allowed.")
    entry = entry / entry_norm

    exit_ = get_quantity(exit_direction, unit=unit)  # type: ignore[arg-type]
    exit_norm = np.linalg.norm(exit_)
    if exit_norm.to_value(exit_.unit) == 0:
        raise ValueError("Zero-length exit_direction is not allowed.")
    exit_ = exit_ / exit_norm

    handle = chord_len / 3
    if turn_radius_hint is not None:
        hint = np.abs(get_quantity(turn_radius_hint, unit=unit))
        if hint.to_value(hint.unit) > 0:
            handle = min(handle, hint)  # type: ignore[arg-type]

    p1 = p0 + entry * handle
    p2 = p3 - exit_ * handle
    return p0, p1, p2, p3


def _curve_metric_length(
    p0: u.Quantity, p1: u.Quantity, p2: u.Quantity, p3: u.Quantity, *, samples: int = 64
) -> u.Quantity:
    s = np.linspace(0.0, 1.0, samples)
    points = (
        ((1 - s) ** 3)[:, None] * p0
        + (3 * (1 - s) ** 2 * s)[:, None] * p1
        + (3 * (1 - s) * s**2)[:, None] * p2
        + (s**3)[:, None] * p3
    )
    diffs = np.diff(points, axis=0)
    seglen = np.linalg.norm(diffs, axis=1)
    return np.sum(seglen)


def _smoothstep7(ratio: np.ndarray) -> np.ndarray:
    return 35 * ratio**4 - 84 * ratio**5 + 70 * ratio**6 - 20 * ratio**7


def _curve_points(
    p0: u.Quantity, p1: u.Quantity, p2: u.Quantity, p3: u.Quantity, *, samples: int
) -> u.Quantity:
    tau = np.linspace(0.0, 1.0, samples)
    s = _smoothstep7(tau)
    return (
        ((1 - s) ** 3)[:, None] * p0
        + (3 * (1 - s) ** 2 * s)[:, None] * p1
        + (3 * (1 - s) * s**2)[:, None] * p2
        + (s**3)[:, None] * p3
    )


def _single_line_edge_profile7(ratio: np.ndarray) -> np.ndarray:
    """Jerk-smooth line-edge profile with terminal slope 2.

    The polynomial satisfies

    - p(0)=0, p'(0)=0, p''(0)=0, p'''(0)=0
    - p(1)=1, p'(1)=2, p''(1)=0, p'''(1)=0

    so an edge segment can start from rest and join a constant-velocity line with
    zero acceleration and zero jerk at the boundary.
    """
    return 5 * ratio**4 - 6 * ratio**5 + 2 * ratio**6


def _single_line_edge_profile7_d1(ratio: np.ndarray) -> np.ndarray:
    return 20 * ratio**3 - 30 * ratio**4 + 12 * ratio**5


def _single_line_edge_profile7_d2(ratio: np.ndarray) -> np.ndarray:
    return 60 * ratio**2 - 120 * ratio**3 + 60 * ratio**4


def _single_line_edge_profile7_d3(ratio: np.ndarray) -> np.ndarray:
    return 120 * ratio - 360 * ratio**2 + 240 * ratio**3


def _single_line_edge_terminal_slope() -> float:
    return 2.0


def _single_line_edge_nominal_duration(speed: u.Quantity, margin: u.Quantity) -> u.Quantity:
    return (_single_line_edge_terminal_slope() * margin / speed).to(u.s)


def evaluate_single_line_edge_kinematics(
    *,
    speed: T,
    margin: T,
    unit: Optional[UnitType] = None,
    limits: Optional[ScanBlockKinematicLimits] = None,
) -> Dict[str, u.Quantity]:
    speed_q = get_quantity(speed, unit=f"{unit}/s")
    margin_q = get_quantity(margin, unit=unit)
    if margin_q.to_value(margin_q.unit) <= 0:
        raise ValueError('Single-line edge margin must be positive.')

    nominal_duration = _single_line_edge_nominal_duration(speed_q, margin_q)
    duration = nominal_duration

    peak_speed_nominal = speed_q
    peak_acc_nominal = (
        np.max(_single_line_edge_profile7_d2(np.linspace(0.0, 1.0, 4097))) * margin_q / nominal_duration**2
    ).to(f"{unit}/s^2")
    peak_jerk_nominal = (
        np.max(np.abs(_single_line_edge_profile7_d3(np.linspace(0.0, 1.0, 4097)))) * margin_q / nominal_duration**3
    ).to(f"{unit}/s^3")

    speed_scale = 1.0
    acceleration_scale = 1.0
    jerk_scale = 1.0
    if limits is not None:
        speed_scale = max(1.0, _dimensionless_value(peak_speed_nominal / limits.max_speed))
        acceleration_scale = max(
            1.0,
            np.sqrt(max(0.0, _dimensionless_value(peak_acc_nominal / limits.max_acceleration))),
        )
        if limits.max_jerk is not None:
            jerk_scale = max(
                1.0,
                np.cbrt(max(0.0, _dimensionless_value(peak_jerk_nominal / limits.max_jerk))),
            )
        duration = nominal_duration * max(speed_scale, acceleration_scale, jerk_scale)

    duration_scale = _dimensionless_value(duration / nominal_duration)
    peak_speed = peak_speed_nominal / duration_scale
    peak_acceleration = peak_acc_nominal / (duration_scale**2)
    peak_jerk = peak_jerk_nominal / (duration_scale**3)
    return {
        'nominal_duration': nominal_duration,
        'duration': duration,
        'nominal_peak_speed': peak_speed_nominal,
        'peak_speed': peak_speed,
        'nominal_peak_acceleration': peak_acc_nominal,
        'peak_acceleration': peak_acceleration,
        'nominal_peak_jerk': peak_jerk_nominal,
        'peak_jerk': peak_jerk,
        'duration_scale': duration_scale * u.dimensionless_unscaled,
        'speed_scale': speed_scale * u.dimensionless_unscaled,
        'acceleration_scale': acceleration_scale * u.dimensionless_unscaled,
        'jerk_scale': jerk_scale * u.dimensionless_unscaled,
        'time_law': 'edge_profile7',
        'terminal_slope': _single_line_edge_terminal_slope() * u.dimensionless_unscaled,
    }


def evaluate_curved_turn_kinematics(
    *,
    start: Tuple[T, T],
    stop: Tuple[T, T],
    entry_direction: Tuple[T, T],
    exit_direction: Tuple[T, T],
    speed: T,
    turn_radius_hint: Optional[T] = None,
    unit: Optional[UnitType] = None,
    limits: Optional[ScanBlockKinematicLimits] = None,
    samples: int = 2001,
) -> Dict[str, u.Quantity]:
    speed_q = get_quantity(speed, unit=f"{unit}/s")
    p0, p1, p2, p3 = _curve_control_points(
        start, stop, entry_direction, exit_direction, turn_radius_hint, unit=unit
    )
    length = _curve_metric_length(p0, p1, p2, p3)
    if length.to_value(length.unit) == 0:
        zero_speed = 0 * speed_q
        zero_acc = 0 * get_quantity(1.0, unit=f"{unit}/s^2")
        zero_jerk = 0 * get_quantity(1.0, unit=f"{unit}/s^3")
        zero_time = 0 * u.s
        return {
            "length": length,
            "nominal_duration": zero_time,
            "duration": zero_time,
            "nominal_peak_speed": zero_speed,
            "peak_speed": zero_speed,
            "nominal_peak_acceleration": zero_acc,
            "peak_acceleration": zero_acc,
            "nominal_peak_jerk": zero_jerk,
            "peak_jerk": zero_jerk,
            "duration_scale": 1.0 * u.dimensionless_unscaled,
            "speed_scale": 1.0 * u.dimensionless_unscaled,
            "acceleration_scale": 1.0 * u.dimensionless_unscaled,
            "jerk_scale": 1.0 * u.dimensionless_unscaled,
            "time_law": "smoothstep7",
        }

    nominal_duration = (length / speed_q).to(u.s)
    points = _curve_points(p0, p1, p2, p3, samples=samples)
    dt = nominal_duration.to_value("s") / max(1, (samples - 1))
    diffs = np.diff(points, axis=0)
    vel = diffs / dt
    speed_mag = np.linalg.norm(vel, axis=1)
    peak_speed_nominal = np.max(speed_mag)
    if len(vel) >= 2:
        acc = np.diff(vel, axis=0) / dt
        acc_mag = np.linalg.norm(acc, axis=1)
        peak_acc_nominal = np.max(acc_mag)
    else:
        acc = None
        peak_acc_nominal = 0 * get_quantity(1.0, unit=f"{unit}/s^2")

    if acc is not None and len(acc) >= 2:
        jerk = np.diff(acc, axis=0) / dt
        jerk_mag = np.linalg.norm(jerk, axis=1)
        peak_jerk_nominal = np.max(jerk_mag)
    else:
        peak_jerk_nominal = 0 * get_quantity(1.0, unit=f"{unit}/s^3")

    duration = nominal_duration
    speed_scale = 1.0
    acceleration_scale = 1.0
    jerk_scale = 1.0
    if limits is not None:
        speed_scale = max(1.0, _dimensionless_value(peak_speed_nominal / limits.max_speed))
        acceleration_scale = max(
            1.0,
            np.sqrt(
                max(
                    0.0,
                    _dimensionless_value(peak_acc_nominal / limits.max_acceleration),
                )
            ),
        )
        if limits.max_jerk is not None:
            jerk_scale = max(
                1.0,
                np.cbrt(
                    max(
                        0.0,
                        _dimensionless_value(peak_jerk_nominal / limits.max_jerk),
                    )
                ),
            )
        duration = nominal_duration * max(speed_scale, acceleration_scale, jerk_scale)

    duration_scale = _dimensionless_value(duration / nominal_duration)
    peak_speed = peak_speed_nominal / duration_scale
    peak_acceleration = peak_acc_nominal / (duration_scale**2)
    peak_jerk = peak_jerk_nominal / (duration_scale**3)
    return {
        "length": length,
        "nominal_duration": nominal_duration,
        "duration": duration,
        "nominal_peak_speed": peak_speed_nominal,
        "peak_speed": peak_speed,
        "nominal_peak_acceleration": peak_acc_nominal,
        "peak_acceleration": peak_acceleration,
        "nominal_peak_jerk": peak_jerk_nominal,
        "peak_jerk": peak_jerk,
        "duration_scale": duration_scale * u.dimensionless_unscaled,
        "speed_scale": speed_scale * u.dimensionless_unscaled,
        "acceleration_scale": acceleration_scale * u.dimensionless_unscaled,
        "jerk_scale": jerk_scale * u.dimensionless_unscaled,
        "time_law": "smoothstep7",
    }


def single_line_required_acceleration(line: ScanBlockLine) -> u.Quantity:
    speed = get_quantity(line.speed)
    margin = get_quantity(line.margin, unit=str(speed.unit).split('/')[0])
    kin = evaluate_single_line_edge_kinematics(speed=speed, margin=margin, unit=str(margin.unit).split()[0])
    return kin['nominal_peak_acceleration']


def plan_scan_block_kinematics(
    lines: Sequence[ScanBlockLine],
    *,
    speed_headroom: float = 1.0,
    acceleration_headroom: float = 1.0,
    jerk_headroom: float = 1.0,
    samples: int = 2001,
) -> Dict[str, Any]:
    limits = conservative_antenna_kinematic_limits(
        speed_headroom=speed_headroom,
        acceleration_headroom=acceleration_headroom,
        jerk_headroom=jerk_headroom,
    )
    line_reports: List[Dict[str, Any]] = []
    for line in lines:
        speed = get_quantity(line.speed)
        margin = get_quantity(line.margin, unit=str(speed.unit).split('/')[0])
        kin = evaluate_single_line_edge_kinematics(speed=speed, margin=margin, unit=str(margin.unit), limits=limits)
        line_reports.append(
            {
                "line_index": line.line_index,
                "label": line.label,
                **kin,
                "required_acceleration": kin["nominal_peak_acceleration"],
                "within_limits": _within_limit(kin["peak_acceleration"], limits.max_acceleration),
                "within_speed_limit": _within_limit(kin["peak_speed"], limits.max_speed),
                "within_acceleration_limit": _within_limit(kin["peak_acceleration"], limits.max_acceleration),
                "within_jerk_limit": (
                    _within_limit(kin["peak_jerk"], limits.max_jerk)
                ),
            }
        )

    turn_reports: List[Dict[str, Any]] = []
    for prev, nxt in zip(lines[:-1], lines[1:]):
        kin = evaluate_curved_turn_kinematics(
            start=margin_stop_of(prev),
            stop=margin_start_of(nxt),
            entry_direction=tuple(_line_unit_vector(prev)),
            exit_direction=tuple(_line_unit_vector(nxt)),
            speed=_resolve_turn_speed(prev, nxt),
            turn_radius_hint=_auto_turn_radius_hint(prev, nxt),
            limits=limits,
            samples=samples,
        )
        turn_reports.append(
            {
                "from_line_index": prev.line_index,
                "to_line_index": nxt.line_index,
                **kin,
                "within_speed_limit": _within_limit(kin["peak_speed"], limits.max_speed),
                "within_acceleration_limit": _within_limit(kin["peak_acceleration"], limits.max_acceleration),
                "within_jerk_limit": (
                    None
                    if limits.max_jerk is None
                    else bool(kin["peak_jerk"] <= limits.max_jerk)
                ),
            }
        )

    return {
        "limits": limits,
        "lines": line_reports,
        "turns": turn_reports,
    }


@dataclass(frozen=True)
class ScanBlockLine:
    """High-level description of one observed line inside a scan block.

    Parameters are interpreted in ``scan_frame`` of the block. ``margin`` is the
    along-scan distance used to define the true standby point

        margin_start = start - unit_vector * margin

    and the final deceleration destination

        margin_stop = stop + unit_vector * margin.
    """

    start: Tuple[T, T]
    stop: Tuple[T, T]
    speed: T
    margin: T
    label: str = ""
    line_index: int = -1


@dataclass(frozen=True)
class ScanBlockSection:
    """Low-level section description consumed by :meth:`PathFinder.scan_block`."""

    kind: str
    start: Tuple[T, T]
    stop: Optional[Tuple[T, T]] = None
    speed: Optional[T] = None
    margin: Optional[T] = None
    duration: Optional[T] = None
    label: str = ""
    line_index: int = -1
    tight: Optional[bool] = None
    turn_radius_hint: Optional[T] = None


class Hold(Path):
    """Hold at a single coordinate for a finite duration."""

    tight = False
    infinite = False
    waypoint = False

    def __init__(
        self,
        calc: CoordCalculator,
        *target: Union[str, DimensionLess, u.Quantity, CoordFrameType],
        unit: Optional[UnitType] = None,
        point: Tuple[T, T],
        frame: CoordFrameType,
        duration: T,
        offset: Optional[Tuple[T, T, CoordFrameType]] = None,
        cos_correction: bool = False,
        **ctx_kw: Any,
    ) -> None:
        super().__init__(calc, *target, unit=unit)
        self._point = get_quantity(point, unit=unit)  # type: ignore[arg-type]
        self._frame = frame
        self._duration = get_quantity(duration, unit="s")
        self._cos_correction = bool(cos_correction)
        self._offset = (
            None
            if offset is None
            else calc.coordinate_delta(
                d_lon=offset[0],
                d_lat=offset[1],
                frame=offset[2],
                unit=unit,
                cos_correction=self._cos_correction,
                cos_correction_ref="here",
            )
        )
        self._ctx_kw = ctx_kw
        require_unit = (
            ((offset is not None) and (not isinstance(offset[0], u.Quantity)))
            or ((len(target) > 0) and (not isinstance(target[0], u.Quantity)))
            or (not isinstance(point[0], u.Quantity))
        )
        if (unit is None) and require_unit:
            raise ValueError(
                "Unit must be specified if any of the following arguments are not "
                "quantities; `target`, `point`, `offset`"
            )
        self._unit = unit

    @property
    def n_cmd(self) -> int:
        return max(
            1,
            int(
                np.ceil(
                    float(self._duration.to_value("s") * self._calc.command_freq)
                )
            ),
        )

    @property
    def target_frame(self) -> CoordFrameType:
        if self._offset is not None:
            return self._offset.frame
        return self._frame

    @property
    def lonlat_func(self) -> Callable[[Index], Tuple[T, T]]:
        def _lonlat_func(idx: Index) -> Tuple[T, T]:
            if self._target is None:
                point = self._calc.coordinate(
                    lon=self._point[0],
                    lat=self._point[1],
                    frame=self._frame,
                    unit=self._unit,
                    time=idx.time,
                )
            else:
                reference = (
                    self._target.realize(time=idx.time)  # type: ignore
                    if hasattr(self._target, "realize")
                    else self._target
                )
                reference = reference.replicate(time=idx.time)
                delta = self._calc.coordinate_delta(
                    d_lon=self._point[0],
                    d_lat=self._point[1],
                    frame=self._frame,
                    cos_correction=self._cos_correction,
                    cos_correction_ref="here",
                )
                point = reference.cartesian_offset_by(delta)
            point = point if self._offset is None else point.cartesian_offset_by(self._offset)
            lon = point.lon * np.ones(len(idx.time))
            lat = point.lat * np.ones(len(idx.time))
            return lon, lat

        return _lonlat_func

    @property
    def arguments(self) -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        ctx_kw = dict(
            tight=self.tight,
            infinite=self.infinite,
            waypoint=self.waypoint,
            duration=float(self._duration.to_value("s")),
        )
        ctx_kw.update(self._ctx_kw)
        return (self.lonlat_func, self.target_frame), {
            "n_cmd": self.n_cmd,
            "context": ControlContext(**ctx_kw),
            "unit": self._unit,
        }


class ScanBlockAccelerate(Linear):
    """Jerk-smooth scan-block entry from standby point to line start."""

    tight = False
    infinite = False
    waypoint = False

    @property
    def _kinematics(self) -> Dict[str, u.Quantity]:
        return evaluate_single_line_edge_kinematics(
            speed=self._speed,
            margin=self._margin,
            unit=self._unit,
            limits=conservative_antenna_kinematic_limits(),
        )

    @property
    def n_cmd(self) -> int:
        duration = self._kinematics['duration']
        return max(1, int(np.ceil(float(duration.to_value('s') * self._calc.command_freq))))

    @property
    def lonlat_func(self) -> Callable[[Index], Tuple[T, T]]:
        unit_scan_vector = self._metric_unit_vector()
        margin_start = self._start - unit_scan_vector * self._margin

        def _lonlat_func(idx: Index) -> Tuple[T, T]:
            if self._target is None:
                kw = dict(frame=self._scan_frame, unit=self._unit, time=idx.time)
                _start = self._calc.coordinate(lon=margin_start[0], lat=margin_start[1], **kw)
                _stop = self._calc.coordinate(lon=self._start[0], lat=self._start[1], **kw)
            else:
                _reference = (
                    self._target.realize(time=idx.time)  # type: ignore
                    if hasattr(self._target, 'realize')
                    else self._target
                )
                _reference = _reference.replicate(time=idx.time)
                ratio = idx.index / self.n_cmd  # type: ignore
                rr = _single_line_edge_profile7(np.asarray(ratio, dtype=float))
                d_lon = margin_start[0] * (1 - rr) + self._start[0] * rr
                d_lat = margin_start[1] * (1 - rr) + self._start[1] * rr
                offset = self._calc.coordinate_delta(
                    d_lon=d_lon, d_lat=d_lat, frame=self._scan_frame,
                    cos_correction=self._cos_correction, cos_correction_ref='here',
                )
                point = _reference.cartesian_offset_by(offset)
                point = point if self._offset is None else point.cartesian_offset_by(self._offset)
                return point.lon, point.lat

            start = _start if self._offset is None else _start.cartesian_offset_by(self._offset)
            stop = _stop if self._offset is None else _stop.cartesian_offset_by(self._offset)
            ratio = idx.index / self.n_cmd  # type: ignore
            rr = _single_line_edge_profile7(np.asarray(ratio, dtype=float))
            lon = start.lon * (1 - rr) + stop.lon * rr
            lat = start.lat * (1 - rr) + stop.lat * rr
            return lon, lat

        return _lonlat_func


class Decelerate(Linear):
    """Mirror of :class:`ScanBlockAccelerate` from line stop to final standby point."""

    tight = False
    infinite = False
    waypoint = False

    @property
    def _kinematics(self) -> Dict[str, u.Quantity]:
        return evaluate_single_line_edge_kinematics(
            speed=self._speed,
            margin=self._margin,
            unit=self._unit,
            limits=conservative_antenna_kinematic_limits(),
        )

    @property
    def n_cmd(self) -> int:
        duration = self._kinematics['duration']
        return max(1, int(np.ceil(float(duration.to_value("s") * self._calc.command_freq))))

    @property
    def lonlat_func(self) -> Callable[[Index], Tuple[T, T]]:
        unit_scan_vector = self._metric_unit_vector()
        margin_stop = self._stop + unit_scan_vector * self._margin

        def _lonlat_func(idx: Index) -> Tuple[T, T]:
            if self._target is None:
                kw = dict(frame=self._scan_frame, unit=self._unit, time=idx.time)
                _start = self._calc.coordinate(
                    lon=self._stop[0], lat=self._stop[1], **kw
                )
                _stop = self._calc.coordinate(
                    lon=margin_stop[0], lat=margin_stop[1], **kw
                )
            else:
                reference = (
                    self._target.realize(time=idx.time)  # type: ignore
                    if hasattr(self._target, "realize")
                    else self._target
                )
                reference = reference.replicate(time=idx.time)
                ratio = idx.index / self.n_cmd  # type: ignore[operator]
                rr = 1.0 - _single_line_edge_profile7(1.0 - np.asarray(ratio, dtype=float))
                d_lon = self._stop[0] * (1 - rr) + margin_stop[0] * rr
                d_lat = self._stop[1] * (1 - rr) + margin_stop[1] * rr
                delta = self._calc.coordinate_delta(
                    d_lon=d_lon,
                    d_lat=d_lat,
                    frame=self._scan_frame,
                    cos_correction=self._cos_correction,
                    cos_correction_ref="here",
                )
                point = reference.cartesian_offset_by(delta)
                point = point if self._offset is None else point.cartesian_offset_by(self._offset)
                return point.lon, point.lat

            start = _start if self._offset is None else _start.cartesian_offset_by(self._offset)
            stop = _stop if self._offset is None else _stop.cartesian_offset_by(self._offset)
            ratio = idx.index / self.n_cmd  # type: ignore[operator]
            rr = 1.0 - _single_line_edge_profile7(1.0 - np.asarray(ratio, dtype=float))
            lon = start.lon * (1 - rr) + stop.lon * rr
            lat = start.lat * (1 - rr) + stop.lat * rr
            return lon, lat

        return _lonlat_func


class CurvedTurn(Path):
    """Rest-to-rest curved turn between two standby points.

    Geometry is defined by a cubic Bezier curve in the scan frame. The time
    parameter uses a septic smoothstep

        σ(τ) = 35τ^4 - 84τ^5 + 70τ^6 - 20τ^7

    so start/end velocity, acceleration, and jerk are all zero.
    """

    tight = False
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
        entry_direction: Tuple[T, T],
        exit_direction: Tuple[T, T],
        speed: T,
        turn_radius_hint: Optional[T] = None,
        offset: Optional[Tuple[T, T, CoordFrameType]] = None,
        cos_correction: bool = False,
        **ctx_kw: Any,
    ) -> None:
        super().__init__(calc, *target, unit=unit)
        self._start = get_quantity(start, unit=unit)  # type: ignore[arg-type]
        self._stop = get_quantity(stop, unit=unit)  # type: ignore[arg-type]
        self._entry_direction = get_quantity(entry_direction, unit=unit)  # type: ignore[arg-type]
        self._exit_direction = get_quantity(exit_direction, unit=unit)  # type: ignore[arg-type]
        self._scan_frame = scan_frame
        self._speed = get_quantity(speed, unit=f"{unit}/s")
        self._turn_radius_hint = (
            None
            if turn_radius_hint is None
            else get_quantity(turn_radius_hint, unit=unit)
        )
        self._cos_correction = bool(cos_correction)
        self._offset = (
            None
            if offset is None
            else calc.coordinate_delta(
                d_lon=offset[0],
                d_lat=offset[1],
                frame=offset[2],
                unit=unit,
                cos_correction=self._cos_correction,
                cos_correction_ref="here",
            )
        )
        self._ctx_kw = ctx_kw

        require_unit = (
            ((offset is not None) and (not isinstance(offset[0], u.Quantity)))
            or ((len(target) > 0) and (not isinstance(target[0], u.Quantity)))
            or (not isinstance(start[0], u.Quantity))
            or (not isinstance(stop[0], u.Quantity))
            or (not isinstance(entry_direction[0], u.Quantity))
            or (not isinstance(exit_direction[0], u.Quantity))
        )
        if (unit is None) and require_unit:
            raise ValueError(
                "Unit must be specified if any of the following arguments are not "
                "quantities; `target`, `start`, `stop`, `entry_direction`, "
                "`exit_direction`, `offset`"
            )
        self._unit = unit

    def _metric_unit_vector(self, vector: u.Quantity) -> u.Quantity:
        norm = np.linalg.norm(vector)
        if norm.to_value(vector.unit) == 0:
            raise ValueError("Zero-length tangent vector is not allowed for CurvedTurn.")
        return vector / norm

    @staticmethod
    def _smoothstep7(ratio: np.ndarray) -> np.ndarray:
        return _smoothstep7(ratio)

    def _control_points(self) -> Tuple[u.Quantity, u.Quantity, u.Quantity, u.Quantity]:
        return _curve_control_points(
            tuple(self._start),
            tuple(self._stop),
            tuple(self._entry_direction),
            tuple(self._exit_direction),
            self._turn_radius_hint,
            unit=self._unit,
        )

    def _metric_length_estimate(self, n: int = 64) -> u.Quantity:
        p0, p1, p2, p3 = self._control_points()
        return _curve_metric_length(p0, p1, p2, p3, samples=n)

    def _planned_duration(self) -> u.Quantity:
        kin = evaluate_curved_turn_kinematics(
            start=tuple(self._start),
            stop=tuple(self._stop),
            entry_direction=tuple(self._entry_direction),
            exit_direction=tuple(self._exit_direction),
            speed=self._speed,
            turn_radius_hint=self._turn_radius_hint,
            unit=self._unit,
            limits=conservative_antenna_kinematic_limits(),
        )
        return kin["duration"].to(u.s)

    @property
    def n_cmd(self) -> int:
        duration = self._planned_duration()
        if duration.to_value("s") == 0:
            return 1
        return max(1, int(np.ceil(float(duration.to_value("s") * self._calc.command_freq))))

    @property
    def target_frame(self) -> CoordFrameType:
        if self._offset is not None:
            return self._offset.frame
        return self._scan_frame

    def _curve_offsets(self, idx: Index) -> Tuple[u.Quantity, u.Quantity]:
        p0, p1, p2, p3 = self._control_points()
        ratio = np.asanyarray(idx.index, dtype=float) / float(self.n_cmd)
        ratio = np.clip(ratio, 0.0, 1.0)
        s = self._smoothstep7(ratio)
        lon = (
            p0[0] * (1 - s) ** 3
            + 3 * p1[0] * (1 - s) ** 2 * s
            + 3 * p2[0] * (1 - s) * s**2
            + p3[0] * s**3
        )
        lat = (
            p0[1] * (1 - s) ** 3
            + 3 * p1[1] * (1 - s) ** 2 * s
            + 3 * p2[1] * (1 - s) * s**2
            + p3[1] * s**3
        )
        return lon, lat

    @property
    def lonlat_func(self) -> Callable[[Index], Tuple[T, T]]:
        def _lonlat_func(idx: Index) -> Tuple[T, T]:
            d_lon, d_lat = self._curve_offsets(idx)
            if self._target is None:
                points = self._calc.coordinate(
                    lon=d_lon,
                    lat=d_lat,
                    frame=self._scan_frame,
                    unit=self._unit,
                    time=idx.time,
                )
                points = (
                    points
                    if self._offset is None
                    else points.cartesian_offset_by(self._offset)
                )
                return points.lon, points.lat

            reference = (
                self._target.realize(time=idx.time)  # type: ignore
                if hasattr(self._target, "realize")
                else self._target
            )
            reference = reference.replicate(time=idx.time)
            delta = self._calc.coordinate_delta(
                d_lon=d_lon,
                d_lat=d_lat,
                frame=self._scan_frame,
                cos_correction=self._cos_correction,
                cos_correction_ref="here",
            )
            points = reference.cartesian_offset_by(delta)
            points = points if self._offset is None else points.cartesian_offset_by(self._offset)
            return points.lon, points.lat

        return _lonlat_func

    @property
    def arguments(self) -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        ctx_kw = dict(
            tight=self.tight,
            infinite=self.infinite,
            waypoint=self.waypoint,
            duration=float(self._planned_duration().to_value("s")),
        )
        ctx_kw.update(self._ctx_kw)
        return (self.lonlat_func, self.target_frame), {
            "n_cmd": self.n_cmd,
            "context": ControlContext(**ctx_kw),
            "unit": self._unit,
        }


def _line_unit_vector(line: ScanBlockLine) -> u.Quantity:
    start = get_quantity(line.start)
    stop = get_quantity(line.stop)
    vector: u.Quantity = stop - start  # type: ignore[operator]
    norm = np.linalg.norm(vector)
    if norm.to_value(vector.unit) == 0:
        raise ValueError("Zero-length scan block line is not allowed.")
    return vector / norm


def margin_start_of(line: ScanBlockLine) -> Tuple[u.Quantity, u.Quantity]:
    unit_vector = _line_unit_vector(line)
    start = get_quantity(line.start)
    margin = get_quantity(line.margin, unit=start[0].unit)  # type: ignore[index]
    point = start - unit_vector * margin
    return point[0], point[1]


def margin_stop_of(line: ScanBlockLine) -> Tuple[u.Quantity, u.Quantity]:
    unit_vector = _line_unit_vector(line)
    stop = get_quantity(line.stop)
    margin = get_quantity(line.margin, unit=stop[0].unit)  # type: ignore[index]
    point = stop + unit_vector * margin
    return point[0], point[1]


def _resolve_turn_speed(prev: ScanBlockLine, nxt: ScanBlockLine) -> T:
    prev_speed = get_quantity(prev.speed)
    next_speed = get_quantity(nxt.speed, unit=str(prev_speed.unit))
    return prev_speed if prev_speed <= next_speed else next_speed


def _auto_turn_radius_hint(prev: ScanBlockLine, nxt: ScanBlockLine) -> u.Quantity:
    prev_margin = get_quantity(prev.margin)
    next_margin = get_quantity(nxt.margin, unit=str(prev_margin.unit))
    start = np.asanyarray(margin_stop_of(prev))
    stop = np.asanyarray(margin_start_of(nxt))
    chord = np.linalg.norm(stop - start)
    return min(prev_margin, next_margin, chord / 3)  # type: ignore[arg-type]


def build_scan_block_sections(
    lines: Sequence[ScanBlockLine],
    *,
    include_initial_standby: bool = True,
    include_final_decelerate: bool = True,
    include_final_standby: bool = False,
    final_standby_duration: T = 1.0 * u.s,
) -> List[ScanBlockSection]:
    if len(lines) == 0:
        raise ValueError("At least one scan block line is required.")

    sections: List[ScanBlockSection] = []
    first = lines[0]
    first_label = first.label or f"line{first.line_index}"
    if include_initial_standby:
        sections.append(
            ScanBlockSection(
                kind="initial_standby",
                start=first.start,
                stop=first.stop,
                speed=first.speed,
                margin=first.margin,
                label=f"{first_label}:initial_standby",
                line_index=first.line_index,
                tight=False,
            )
        )

    for i, line in enumerate(lines):
        label = line.label or f"line{line.line_index}"
        sections.append(
            ScanBlockSection(
                kind="accelerate",
                start=line.start,
                stop=line.stop,
                speed=line.speed,
                margin=line.margin,
                label=f"{label}:accelerate",
                line_index=line.line_index,
                tight=False,
            )
        )
        sections.append(
            ScanBlockSection(
                kind="line",
                start=line.start,
                stop=line.stop,
                speed=line.speed,
                margin=line.margin,
                label=label,
                line_index=line.line_index,
                tight=True,
            )
        )

        if i + 1 < len(lines):
            nxt = lines[i + 1]
            sections.append(
                ScanBlockSection(
                    kind="decelerate",
                    start=line.start,
                    stop=line.stop,
                    speed=line.speed,
                    margin=line.margin,
                    label=f"{label}:decelerate",
                    line_index=line.line_index,
                    tight=False,
                )
            )
            sections.append(
                ScanBlockSection(
                    kind="turn",
                    start=margin_stop_of(line),
                    stop=margin_start_of(nxt),
                    speed=_resolve_turn_speed(line, nxt),
                    label=f"turn:{line.line_index}->{nxt.line_index}",
                    line_index=nxt.line_index,
                    tight=False,
                    turn_radius_hint=_auto_turn_radius_hint(line, nxt),
                )
            )

    last = lines[-1]
    if include_final_decelerate:
        label = last.label or f"line{last.line_index}"
        sections.append(
            ScanBlockSection(
                kind="decelerate",
                start=last.start,
                stop=last.stop,
                speed=last.speed,
                margin=last.margin,
                label=f"{label}:final_decelerate",
                line_index=last.line_index,
                tight=False,
            )
        )

    if include_final_standby:
        label = last.label or f"line{last.line_index}"
        sections.append(
            ScanBlockSection(
                kind="final_standby",
                start=margin_stop_of(last),
                speed=last.speed,
                duration=final_standby_duration,
                label=f"{label}:final_standby",
                line_index=last.line_index,
                tight=False,
            )
        )

    return sections