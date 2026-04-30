from __future__ import annotations

import math

import numpy as np


def _smoothstep7(t):
    return 35.0 * t**4 - 84.0 * t**5 + 70.0 * t**6 - 20.0 * t**7


def _bezier_point(t, p0, p1, p2, p3):
    return (
        ((1 - t) ** 3)[:, None] * p0
        + (3 * (1 - t) ** 2 * t)[:, None] * p1
        + (3 * (1 - t) * t**2)[:, None] * p2
        + (t**3)[:, None] * p3
    )


def _curve_samples(
    start, stop, entry_dir, exit_dir, turn_radius_hint, speed_deg_s, n=4001
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
    s = _smoothstep7(tau)
    pts = _bezier_point(s, p0, p1, p2, p3)
    seg = np.diff(pts, axis=0)
    length = np.linalg.norm(seg, axis=1).sum()
    duration = length / float(speed_deg_s)
    dt = duration / (n - 1)
    vel = np.diff(pts, axis=0) / dt
    spd = np.linalg.norm(vel, axis=1)
    acc = np.diff(vel, axis=0) / dt
    acc_mag = np.linalg.norm(acc, axis=1)
    jerk = np.diff(acc, axis=0) / dt
    jerk_mag = np.linalg.norm(jerk, axis=1)
    return dict(
        length=length,
        duration=duration,
        peak_speed=spd.max(),
        peak_acc=acc_mag.max(),
        peak_jerk=jerk_mag.max(),
        start_speed=spd[0],
        end_speed=spd[-1],
        start_acc=acc_mag[0],
        end_acc=acc_mag[-1],
        start_jerk=jerk_mag[0],
        end_jerk=jerk_mag[-1],
    )


def test_curved_turn_rest_to_rest_endpoint_speeds_are_near_zero():
    sim = _curve_samples(
        start=(1.1, 0.0),
        stop=(-0.1, 0.2),
        entry_dir=(1.0, 0.0),
        exit_dir=(-1.0, 0.0),
        turn_radius_hint=0.1,
        speed_deg_s=0.5,
    )
    assert sim["start_speed"] < 0.01
    assert sim["end_speed"] < 0.01


def test_curved_turn_uturn_family_has_consistent_speed_amplification():
    ratios = []
    for dy in (0.1, 0.2, 0.3):
        for radius in (0.05, 0.1, 0.15):
            sim = _curve_samples(
                start=(1.0 + radius, 0.0),
                stop=(-radius, dy),
                entry_dir=(1.0, 0.0),
                exit_dir=(-1.0, 0.0),
                turn_radius_hint=radius,
                speed_deg_s=0.5,
            )
            ratios.append(sim["peak_speed"] / 0.5)
            assert math.isfinite(sim["peak_speed"])
            assert math.isfinite(sim["peak_acc"])
    assert min(ratios) > 1.0
    assert max(ratios) > 2.0


def test_single_line_discrete_acceleration_matches_analytic_formula():
    speed = 0.5
    margin = 0.1
    # accelerate profile rr = ratio^2 on distance from start-margin to start
    n = 10001
    ratio = np.linspace(0.0, 1.0, n)
    pos = -margin + margin * ratio**2
    # choose duration so terminal speed is exactly `speed`
    duration = 2.0 * margin / speed
    dt = duration / (n - 1)
    vel = np.diff(pos) / dt
    acc = np.diff(vel) / dt
    analytic = speed**2 / (2.0 * margin)
    assert abs(acc.mean() - analytic) < 1e-3
    assert abs(vel[-1] - speed) < 1e-4


def test_curved_turn_septic_time_law_keeps_endpoint_acceleration_and_jerk_small():
    sim = _curve_samples(
        start=(1.1, 0.0),
        stop=(-0.1, 0.2),
        entry_dir=(1.0, 0.0),
        exit_dir=(-1.0, 0.0),
        turn_radius_hint=0.1,
        speed_deg_s=0.5,
        n=12001,
    )
    assert sim["start_acc"] < 0.02
    assert sim["end_acc"] < 0.02
    assert sim["start_jerk"] < 0.5
    assert sim["end_jerk"] < 0.5


def test_single_line_edge_profile7_keeps_line_boundary_acceleration_and_jerk_small():
    speed = 0.5
    margin = 0.1
    n = 20001
    ratio = np.linspace(0.0, 1.0, n)
    rr = 5 * ratio**4 - 6 * ratio**5 + 2 * ratio**6
    pos = -margin + margin * rr
    duration = 2.0 * margin / speed
    dt = duration / (n - 1)
    vel = np.diff(pos) / dt
    acc = np.diff(vel) / dt
    jerk = np.diff(acc) / dt
    assert abs(vel[-1] - speed) < 2e-4
    assert abs(acc[-1]) < 0.02
    assert abs(jerk[-1]) < 0.5
