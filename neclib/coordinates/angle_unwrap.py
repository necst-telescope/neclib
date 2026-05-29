"""Angle unwrap helpers for absolute modulo encoders.

This module is intentionally independent from ROS and device drivers.  It converts
an absolute modulo azimuth reading (for example 0..360 deg) into a continuous
azimuth angle within a configured mechanical drive range.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import floor, isfinite
from typing import List, Optional


class AngleUnwrapError(RuntimeError):
    """Base class for absolute encoder unwrap errors."""


class AmbiguousBranchError(AngleUnwrapError):
    """Raised when a raw modulo angle maps to multiple valid branches."""


class NoValidBranchError(AngleUnwrapError):
    """Raised when no continuous candidate is inside the drive range."""


class BranchJumpError(AngleUnwrapError):
    """Raised when the selected continuous angle jumps implausibly."""


class RawAngleRangeError(AngleUnwrapError):
    """Raised when an absolute encoder raw angle is unusable."""


@dataclass(frozen=True)
class AngleUnwrapResult:
    raw_deg: float
    modulo_deg: float
    continuous_deg: float
    branch: int
    branch_changed: bool
    state: str


@dataclass(frozen=True)
class AbsoluteModuloUnwrapConfig:
    enabled: bool = False
    period_deg: float = 360.0
    raw_min_deg: float = 0.0
    raw_max_deg: float = 360.0
    drive_min_deg: float = 0.0
    drive_max_deg: float = 360.0
    zero_offset_deg: float = 0.0
    sign: int = 1
    max_jump_deg: Optional[float] = None

    def validate(self) -> None:
        if not self.enabled:
            return
        if not isfinite(self.period_deg) or self.period_deg <= 0:
            raise ValueError(f"period_deg must be positive: {self.period_deg!r}")
        if not isfinite(self.raw_min_deg) or not isfinite(self.raw_max_deg):
            raise ValueError("raw_min_deg/raw_max_deg must be finite")
        if not isfinite(self.drive_min_deg) or not isfinite(self.drive_max_deg):
            raise ValueError("drive_min_deg/drive_max_deg must be finite")
        if self.drive_min_deg >= self.drive_max_deg:
            raise ValueError(
                f"drive range must be increasing: "
                f"{self.drive_min_deg!r}, {self.drive_max_deg!r}"
            )
        if self.raw_min_deg >= self.raw_max_deg:
            raise ValueError(
                f"raw range must be increasing: {self.raw_min_deg!r}, "
                f"{self.raw_max_deg!r}"
            )
        raw_width = self.raw_max_deg - self.raw_min_deg
        if raw_width > self.period_deg + 1e-9:
            raise ValueError(
                f"raw range width must not exceed period_deg: width={raw_width!r}, "
                f"period={self.period_deg!r}"
            )
        if self.sign not in (-1, 1):
            raise ValueError(f"sign must be +1 or -1: {self.sign!r}")
        if self.max_jump_deg is not None and self.max_jump_deg <= 0:
            raise ValueError(f"max_jump_deg must be positive: {self.max_jump_deg!r}")


def _raw_range_is_full_period(cfg: AbsoluteModuloUnwrapConfig) -> bool:
    return (
        abs((float(cfg.raw_max_deg) - float(cfg.raw_min_deg)) - float(cfg.period_deg))
        <= 1e-9
    )


def _assert_raw_usable(raw_deg: float, cfg: AbsoluteModuloUnwrapConfig) -> None:
    raw = float(raw_deg)
    if not isfinite(raw):
        raise RawAngleRangeError(f"raw angle must be finite: {raw_deg!r}")

    # A full-period raw range such as [0, 360] describes an absolute modulo
    # encoder.  Some devices/drivers can emit a periodic alias at startup, e.g.
    # 727 deg = 2 * 360 + 7 deg.  Treat finite aliases as usable and normalize
    # them below, instead of suppressing the first encoder sample.  For a
    # deliberately narrower raw range, keep the stricter range check.
    if _raw_range_is_full_period(cfg):
        return

    eps = 1e-9
    if not ((cfg.raw_min_deg - eps) <= raw <= (cfg.raw_max_deg + eps)):
        raise RawAngleRangeError(
            f"raw angle {raw:.6f} deg is outside configured range "
            f"[{cfg.raw_min_deg:.6f}, {cfg.raw_max_deg:.6f}] deg"
        )


def normalize_absolute_modulo_raw(
    raw_deg: float, cfg: AbsoluteModuloUnwrapConfig
) -> float:
    """Return the calibrated modulo angle for a finite absolute-encoder raw value.

    For a full-period raw range, finite periodic aliases outside the nominal raw
    range are accepted and folded back into the configured modulo interval.  This
    preserves startup samples such as 727 deg while still rejecting NaN/inf and
    respecting stricter partial raw ranges.
    """
    _assert_raw_usable(raw_deg, cfg)
    calibrated = cfg.sign * float(raw_deg) + cfg.zero_offset_deg
    return ((calibrated - cfg.raw_min_deg) % cfg.period_deg) + cfg.raw_min_deg


def _normalize_modulo(raw_deg: float, cfg: AbsoluteModuloUnwrapConfig) -> float:
    return normalize_absolute_modulo_raw(raw_deg, cfg)


def _continuous_modulo(continuous_deg: float, cfg: AbsoluteModuloUnwrapConfig) -> float:
    return (
        (float(continuous_deg) - cfg.raw_min_deg) % cfg.period_deg
    ) + cfg.raw_min_deg


def continuous_candidates(
    raw_deg: float,
    cfg: AbsoluteModuloUnwrapConfig,
    *,
    margin_periods: int = 1,
) -> List[float]:
    """Return valid continuous candidates for one raw modulo reading."""
    cfg.validate()
    modulo = _normalize_modulo(raw_deg, cfg)
    k_min = int(floor((cfg.drive_min_deg - modulo) / cfg.period_deg)) - margin_periods
    k_max = int(floor((cfg.drive_max_deg - modulo) / cfg.period_deg)) + margin_periods
    out = []
    eps = 1e-9
    for k in range(k_min, k_max + 1):
        c = modulo + k * cfg.period_deg
        if (cfg.drive_min_deg - eps) <= c <= (cfg.drive_max_deg + eps):
            out.append(float(c))
    return sorted(out)


class AbsoluteModuloUnwrapper:
    """Stateful unwrap calculator for one absolute modulo encoder axis."""

    def __init__(
        self,
        cfg: AbsoluteModuloUnwrapConfig,
        *,
        previous_continuous_deg: Optional[float] = None,
    ) -> None:
        cfg.validate()
        self.cfg = cfg
        self.previous_continuous_deg = previous_continuous_deg
        self.previous_branch: Optional[int] = None
        if previous_continuous_deg is not None:
            modulo = _continuous_modulo(previous_continuous_deg, cfg)
            self.previous_branch = self.branch_for(previous_continuous_deg, modulo)

    def branch_for(self, continuous_deg: float, modulo_deg: float) -> int:
        return int(
            round((float(continuous_deg) - float(modulo_deg)) / self.cfg.period_deg)
        )

    def unwrap(self, raw_deg: float) -> AngleUnwrapResult:
        if not self.cfg.enabled:
            value = float(raw_deg)
            return AngleUnwrapResult(
                raw_deg=value,
                modulo_deg=value,
                continuous_deg=value,
                branch=0,
                branch_changed=False,
                state="disabled",
            )

        modulo = _normalize_modulo(raw_deg, self.cfg)
        candidates = continuous_candidates(raw_deg, self.cfg)
        if not candidates:
            raise NoValidBranchError(
                f"No valid continuous Az candidate for raw={raw_deg!r}, "
                f"drive=[{self.cfg.drive_min_deg}, {self.cfg.drive_max_deg}]"
            )

        if self.previous_continuous_deg is None:
            if len(candidates) != 1:
                raise AmbiguousBranchError(
                    f"Ambiguous absolute encoder branch for raw={raw_deg!r}: "
                    f"candidates={candidates}"
                )
            selected = candidates[0]
        else:
            selected = min(
                candidates, key=lambda c: abs(c - self.previous_continuous_deg)
            )
            jump = abs(selected - self.previous_continuous_deg)
            if self.cfg.max_jump_deg is not None and jump > self.cfg.max_jump_deg:
                raise BranchJumpError(
                    f"Implausible absolute encoder jump: previous="
                    f"{self.previous_continuous_deg:.6f} deg, "
                    f"selected={selected:.6f} deg, "
                    f"jump={jump:.6f} deg, max={self.cfg.max_jump_deg:.6f} deg"
                )

        branch = self.branch_for(selected, modulo)
        branch_changed = (self.previous_branch is not None) and (
            branch != self.previous_branch
        )
        self.previous_continuous_deg = selected
        self.previous_branch = branch
        return AngleUnwrapResult(
            raw_deg=float(raw_deg),
            modulo_deg=float(modulo),
            continuous_deg=float(selected),
            branch=int(branch),
            branch_changed=bool(branch_changed),
            state="ok",
        )
