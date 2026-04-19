from __future__ import annotations

import math

import numpy as np


def _smoothstep5(t):
    return 10.0 * t**3 - 15.0 * t**4 + 6.0 * t**5


def _bezier_point(t, p0, p1, p2, p3):
    return (
        ((1 - t) ** 3)[:, None] * p0
        + (3 * (1 - t) ** 2 * t)[:, None] * p1
        + (3 * (1 - t) * t**2)[:, None] * p2
        + (t**3)[:, None] * p3
    )


def _curve_samples(
    start, stop, entry_dir, exit_dir, turn_radius_hint, speed_deg_s, n=2001
):
    p0 = np.asarray(start, dtype=float)
    p3 = np.asarray(stop, dtype=float)
    chord = p3 - p0
    chord_len = np.linalg.norm(chord)
    entry = np.asarray(entry_dir, dtype=float)
    entry = entry / np.linalg.norm(entry)
    exit = np.asarray(exit_dir, dtype=float)
    exit = exit / np.linalg.norm(exit)
    handle = min(chord_len / 3.0, abs(float(turn_radius_hint)))
    p1 = p0 + entry * handle
    p2 = p3 - exit * handle
    tau = np.linspace(0.0, 1.0, n)
    s = _smoothstep5(tau)
    pts = _bezier_point(s, p0, p1, p2, p3)
    seg = np.diff(pts, axis=0)
    length = np.linalg.norm(seg, axis=1).sum()
    duration = length / float(speed_deg_s)
    dt = duration / (n - 1)
    vel = np.diff(pts, axis=0) / dt
    spd = np.linalg.norm(vel, axis=1)
    acc = np.diff(vel, axis=0) / dt
    acc_mag = np.linalg.norm(acc, axis=1)
    return dict(
        length=length, duration=duration, peak_speed=spd.max(), peak_acc=acc_mag.max()
    )


def test_curved_turn_peak_speed_is_reported_not_assumed():
    sim = _curve_samples(
        start=(1.1, 0.0),
        stop=(-0.1, 0.2),
        entry_dir=(1.0, 0.0),
        exit_dir=(-1.0, 0.0),
        turn_radius_hint=0.1,
        speed_deg_s=0.5,
    )
    assert sim["peak_speed"] > 0.5
    assert sim["duration"] > 0.0


def test_curved_turn_representative_u_turn_exceeds_acc_limit_under_current_params():
    sim = _curve_samples(
        start=(1.1, 0.0),
        stop=(-0.1, 0.2),
        entry_dir=(1.0, 0.0),
        exit_dir=(-1.0, 0.0),
        turn_radius_hint=0.1,
        speed_deg_s=0.5,
    )
    representative_acc_limit = 1.0
    assert sim["peak_acc"] > representative_acc_limit


def test_single_line_speed_margin_guard_examples():
    def required_margin(speed_deg_s, acc_limit_deg_s2):
        return (speed_deg_s**2) / (2.0 * acc_limit_deg_s2)

    assert math.isclose(required_margin(0.5, 1.0), 0.125)
    assert required_margin(0.5, 1.0) > 0.1
    assert required_margin(0.2, 1.0) < 0.1
