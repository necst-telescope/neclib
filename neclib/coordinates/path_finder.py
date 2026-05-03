import math
import time
from dataclasses import dataclass
from itertools import count
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    Iterable,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    overload,
)

import astropy.units as u
import numpy as np

from ..core.types import CoordFrameType, DimensionLess, UnitType
from . import paths
from .convert import CoordCalculator


@dataclass
class ApparentAltAzCoordinate:
    az: u.Quantity
    """Azimuth angle."""
    el: u.Quantity
    """Elevation angle."""
    dAz: u.Quantity
    """delta Azimuth angle."""
    dEl: u.Quantity
    """delta Elevation angle."""
    time: List[float]
    """Time for each coordinate."""
    context: paths.ControlContext
    """Metadata of the control section this coordinate object is a part of."""


T = TypeVar("T", bound=Union[DimensionLess, u.Quantity])
CoordinateGenerator = Generator[ApparentAltAzCoordinate, Literal[True], None]


class PathFinder(CoordCalculator):
    # ---------------------------------------------------------------------
    # Optional safety/performance knobs (disabled by default unless set).
    #
    # - command_offset_sec_bootstrap:
    #     Lead time (seconds) used only when a section starts with context.start=None.
    #     If unset, falls back to self.command_offset_sec (default behavior).
    #
    # - command_start_min_lead_sec:
    #     Minimum lead time (seconds) enforced for *any* computed context.start.
    #     If the generator is lagging and would start in the past, this can clamp the
    #     start time to (now + lead). Leave unset/0 to preserve existing behavior.
    #
    # IMPORTANT:
    #   If upstream components filter commands by a larger fixed offset (e.g. 3 s),
    #   setting a smaller bootstrap lead here will NOT reduce perceived delay and may
    #   just increase dropped commands. Tune consistently across the pipeline.
    # ---------------------------------------------------------------------
    def _get_lead_seconds(self, value: Any, *, default: float) -> float:
        """Parse lead time value into seconds."""
        if value is None:
            return float(default)
        if isinstance(value, u.Quantity):
            return float(value.to_value(u.s))
        try:
            return float(value)
        except Exception:
            return float(default)

    def _command_start_bootstrap_lead_sec(self) -> float:
        """Lead time for the first block of a new section."""
        return self._get_lead_seconds(
            getattr(self, "command_offset_sec_bootstrap", None),
            default=float(self.command_offset_sec),
        )

    def _command_start_min_lead_sec(self) -> float:
        """Minimum lead time enforced for any start time."""
        return self._get_lead_seconds(
            getattr(self, "command_start_min_lead_sec", 0.0),
            default=0.0,
        )

    def _clamp_start_time(self, start_time: float) -> float:
        """Clamp start time to be at least (now + command_start_min_lead_sec)."""
        lead = self._command_start_min_lead_sec()
        if lead <= 0:
            return start_time
        now = time.time()
        min_start = now + lead
        return start_time if start_time >= min_start else min_start

    @overload
    def from_function(
        self,
        lon: Callable[[paths.Index], T],
        lat: Callable[[paths.Index], T],
        frame: CoordFrameType,
        /,
        *,
        unit: Optional[UnitType] = None,
        n_cmd: Union[int, float],
        context: paths.ControlContext,
    ) -> CoordinateGenerator: ...

    @overload
    def from_function(
        self,
        lon_lat: Callable[[paths.Index], Tuple[T, T]],
        frame: CoordFrameType,
        /,
        *,
        unit: Optional[UnitType] = None,
        n_cmd: Union[int, float],
        context: paths.ControlContext,
    ) -> CoordinateGenerator: ...

    def from_function(
        self,
        *coord: Union[
            Callable[[paths.Index], T],
            Callable[[paths.Index], Tuple[T, T]],
            CoordFrameType,
        ],
        unit: Optional[UnitType] = None,
        n_cmd: Union[int, float],
        context: paths.ControlContext,
    ) -> CoordinateGenerator:
        """Generate coordinate commands from arbitrary function."""
        if len(coord) == 3:
            lon_func, lat_func, frame = coord

            def lon_lat_func(idx: paths.Index) -> Tuple[T, T]:
                return lon_func(idx), lat_func(idx)  # type: ignore

        elif len(coord) == 2:
            lon_lat_func, frame = coord  # type: ignore
        else:
            raise TypeError(
                "Invalid number of positional arguments: expected 2 ("
                "func(idx)->(lon, lat) and coordinate_frame) or 3 (for func1(idx)->lon,"
                f" func2(idx)->lat and coordinate_frame), but got {len(coord)}"
            )

        unit_n_cmd = int(self.command_group_duration_sec * self.command_freq)
        if context.start is None:
            context.start = time.time() + self._command_start_bootstrap_lead_sec()
        # Optional clamp (useful when generator lags and would start in the past)
        context.start = self._clamp_start_time(context.start)
        if context.stop is None:
            context.stop = context.start + n_cmd / self.command_freq

        for seq in range(math.ceil(n_cmd / unit_n_cmd)):
            start_idx = seq * unit_n_cmd
            _idx = [start_idx + i for i in range(unit_n_cmd) if start_idx + i <= n_cmd]
            _t = [context.start + i / self.command_freq for i in _idx]
            idx = paths.Index(time=_t, index=_idx)

            lon_for_this_seq, lat_for_this_seq = lon_lat_func(idx)
            _coord = self.coordinate(
                lon=lon_for_this_seq,
                lat=lat_for_this_seq,
                frame=frame,  # type: ignore
                unit=unit,
                time=idx.time,
            )
            altaz = _coord.to_apparent_altaz()
            sent = yield ApparentAltAzCoordinate(
                az=altaz.az,  # type: ignore
                el=altaz.alt,  # type: ignore
                dAz=altaz.dAz,  # type: ignore
                dEl=altaz.dEl,  # type: ignore
                time=_t,
                context=context,
            )
            if (sent is not None) and context.waypoint:
                context.stop = idx.time[-1]
                break

    def sequential(
        self,
        *section_args: Tuple[Sequence[Any], Dict[str, Any]],
        repeat: Union[int, Sequence[int]] = 1,
    ) -> CoordinateGenerator:
        if isinstance(repeat, int):
            counter = [range(repeat) if repeat > 0 else count()] * len(section_args)
        else:
            counter = [range(n) if n > 0 else count() for n in repeat]

        last_stop = None
        to_break = False

        ctx = paths.ControlContext()

        for c, (args, kwargs) in zip(counter, section_args):
            for _ in c:
                context: paths.ControlContext = kwargs["context"]
                ctx.update(context)

                # Independent path calculators may not know when the computed command
                # will be sent, especially when the path follows another path. They just
                # know how long it takes to complete the commands they computed. So the
                # time consistency is computed here.
                if context.duration is not None:
                    base_start = (
                        last_stop
                        if last_stop is not None
                        else time.time() + self._command_start_bootstrap_lead_sec()
                    )
                    context.start = self._clamp_start_time(base_start)
                    context.stop = context.start + context.duration
                last_stop = context.stop

                section = self.from_function(*args, **kwargs)
                for coord in section:
                    sent = yield coord
                    if (sent is not None) and coord.context.waypoint:
                        to_break = True
                        context.stop = last_stop = coord.time[-1]

                if to_break:
                    to_break = False
                    break

    def linear(
        self,
        *target: Union[DimensionLess, u.Quantity, str, CoordFrameType],
        unit: Optional[UnitType] = None,
        start: Tuple[T, T],
        stop: Tuple[T, T],
        scan_frame: CoordFrameType,
        speed: T,
        margin: Optional[T] = None,
        offset: Optional[Tuple[T, T, CoordFrameType]] = None,
        cos_correction: bool = False,
    ) -> CoordinateGenerator:
        args = (self, *target)
        kwargs = dict(
            unit=unit,
            start=start,
            stop=stop,
            scan_frame=scan_frame,
            speed=speed,
            margin=margin,
            offset=offset,
            cos_correction=cos_correction,
        )
        path1 = paths.Standby(*args, **kwargs)  # type: ignore
        path2 = paths.Accelerate(*args, **kwargs)  # type: ignore
        path3 = paths.Linear(*args, **kwargs)  # type: ignore
        arguments1 = path1.arguments
        arguments2 = path2.arguments
        arguments3 = path3.arguments

        yield from self.sequential(
            arguments1,
            arguments2,
            arguments3,
            repeat=[-1, 1, 1],
        )

    def scan_block(
        self,
        *target: Union[DimensionLess, u.Quantity, str, CoordFrameType],
        unit: Optional[UnitType] = None,
        scan_frame: CoordFrameType,
        sections: Sequence[paths.ScanBlockSection],
        offset: Optional[Tuple[T, T, CoordFrameType]] = None,
        cos_correction: bool = False,
    ) -> CoordinateGenerator:
        if len(sections) == 0:
            raise ValueError("scan_block requires at least one section.")

        def _direction_from_section(section: paths.ScanBlockSection) -> u.Quantity:
            if section.stop is None:
                raise ValueError(
                    f"Section {section.kind!r} requires stop to infer direction."
                )
            start = u.Quantity(section.start)
            stop = u.Quantity(section.stop)
            vec = stop - start
            norm = np.linalg.norm(vec)
            if norm.to_value(vec.unit) == 0:
                raise ValueError(
                    f"Zero-length section cannot define turn tangent: {section.kind!r}"
                )
            return vec / norm

        def _nearest_direction(idx: int, step: int) -> u.Quantity:
            j = idx + step
            while 0 <= j < len(sections):
                cand = sections[j]
                if cand.kind in {
                    "accelerate",
                    "line",
                    "decelerate",
                    "final_decelerate",
                }:
                    return _direction_from_section(cand)
                j += step
            raise ValueError(
                "Cannot infer turn tangent from neighbouring scan sections."
            )

        section_args = []
        repeats = []
        for i, section in enumerate(sections):
            ctx_kw = dict(
                kind=section.kind,
                label=section.label,
                line_index=section.line_index,
            )
            if section.tight is not None:
                ctx_kw["tight"] = bool(section.tight)

            common_kwargs = dict(
                unit=unit,
                scan_frame=scan_frame,
                offset=offset,
                cos_correction=cos_correction,
                **ctx_kw,
            )

            if section.kind == "initial_standby":
                if (
                    (section.stop is None)
                    or (section.speed is None)
                    or (section.margin is None)
                ):
                    raise ValueError("initial_standby requires stop, speed and margin.")
                path = paths.Standby(
                    self,
                    *target,
                    start=section.start,
                    stop=section.stop,
                    speed=section.speed,
                    margin=section.margin,
                    **common_kwargs,
                )
                repeat = -1
            elif section.kind == "accelerate":
                if (
                    (section.stop is None)
                    or (section.speed is None)
                    or (section.margin is None)
                ):
                    raise ValueError("accelerate requires stop, speed and margin.")
                path = paths.ScanBlockAccelerate(
                    self,
                    *target,
                    start=section.start,
                    stop=section.stop,
                    speed=section.speed,
                    margin=section.margin,
                    **common_kwargs,
                )
                repeat = 1
            elif section.kind == "line":
                if (
                    (section.stop is None)
                    or (section.speed is None)
                    or (section.margin is None)
                ):
                    raise ValueError("line requires stop, speed and margin.")
                path = paths.Linear(
                    self,
                    *target,
                    start=section.start,
                    stop=section.stop,
                    speed=section.speed,
                    margin=section.margin,
                    **common_kwargs,
                )
                repeat = 1
            elif section.kind in {"decelerate", "final_decelerate"}:
                if (
                    (section.stop is None)
                    or (section.speed is None)
                    or (section.margin is None)
                ):
                    raise ValueError("decelerate requires stop, speed and margin.")
                path = paths.Decelerate(
                    self,
                    *target,
                    start=section.start,
                    stop=section.stop,
                    speed=section.speed,
                    margin=section.margin,
                    **common_kwargs,
                )
                repeat = 1
            elif section.kind == "turn":
                if (section.stop is None) or (section.speed is None):
                    raise ValueError("turn requires stop and speed.")
                entry_direction = tuple(_nearest_direction(i, -1))
                exit_direction = tuple(_nearest_direction(i, +1))
                path = paths.CurvedTurn(
                    self,
                    *target,
                    start=section.start,
                    stop=section.stop,
                    speed=section.speed,
                    entry_direction=entry_direction,
                    exit_direction=exit_direction,
                    turn_radius_hint=section.turn_radius_hint,
                    **common_kwargs,
                )
                repeat = 1
            elif section.kind == "final_standby":
                if section.duration is None:
                    raise ValueError("final_standby requires duration.")
                path = paths.Hold(
                    self,
                    *target,
                    point=section.start,
                    frame=scan_frame,
                    duration=section.duration,
                    offset=offset,
                    cos_correction=cos_correction,
                    **ctx_kw,
                )
                repeat = 1
            else:
                raise ValueError(
                    f"Unsupported scan block section kind: {section.kind!r}"
                )

            section_args.append(path.arguments)
            repeats.append(repeat)

        yield from self.sequential(*section_args, repeat=repeats)

    def track(
        self,
        *target: Union[DimensionLess, u.Quantity, str, CoordFrameType],
        unit: Optional[UnitType] = None,
        offset: Optional[Tuple[T, T, CoordFrameType]] = None,
        cos_correction: bool = False,
        **ctx_kw: Any,
    ) -> CoordinateGenerator:
        path = paths.Track(
            self,
            *target,
            unit=unit,
            offset=offset,
            cos_correction=cos_correction,
            **ctx_kw,
        )
        arguments = path.arguments
        yield from self.sequential(
            arguments,
            repeat=-1,
        )


class CoordinateGeneratorManager:
    def __init__(self, generator: Optional[CoordinateGenerator] = None) -> None:
        self._generator = generator
        self._send_value = None

    def will_send(self, value: Any) -> None:
        self._send_value = value

    def __iter__(self) -> Iterable[Any]:
        return self  # type: ignore

    def __next__(self) -> Any:
        if self._generator is None:
            self._send_value = None
            raise StopIteration("No generator attached")
        if self._send_value is None:
            return next(self._generator)
        try:
            ret = self._generator.send(self._send_value)
            self._send_value = None
            return ret
        except TypeError:
            # Keep send value once for just-started generator
            return next(self._generator)

    def attach(self, generator: CoordinateGenerator) -> None:
        self.clear()
        self._generator = generator

    def clear(self) -> None:
        if self._generator is not None:
            try:
                self._generator.close()
            except Exception:
                pass
        self._generator = None

    def get(self) -> Optional[CoordinateGenerator]:
        return self._generator
