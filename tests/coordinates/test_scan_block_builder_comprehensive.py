from __future__ import annotations

from pathlib import Path

import pytest

from tests._helpers.scan_block_stub_runtime import load_scan_block_module, q


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE = load_scan_block_module(REPO_ROOT)


def _line(idx, *, start=(0.0, 0.0), stop=(1.0, 0.0), speed=0.5, margin=0.1, label=None):
    return MODULE.ScanBlockLine(
        start=(q(start[0]), q(start[1])),
        stop=(q(stop[0]), q(stop[1])),
        speed=q(speed, "deg/s"),
        margin=q(margin),
        label=label or f"L{idx}",
        line_index=idx,
    )


def test_build_scan_block_sections_rejects_empty_lines():
    with pytest.raises(ValueError, match="At least one scan block line"):
        MODULE.build_scan_block_sections([])


def test_line_unit_vector_rejects_zero_length_line():
    line = _line(0, start=(1.0, 2.0), stop=(1.0, 2.0))
    with pytest.raises(ValueError, match="Zero-length"):
        MODULE._line_unit_vector(line)


def test_margin_start_stop_and_turn_helpers():
    prev = _line(0, start=(0.0, 0.0), stop=(1.0, 0.0), speed=0.7, margin=0.3)
    nxt = _line(1, start=(1.0, 0.2), stop=(0.0, 0.2), speed=0.5, margin=0.1)

    ms = MODULE.margin_start_of(prev)
    me = MODULE.margin_stop_of(prev)
    assert ms[0].to_value("deg") == -0.3
    assert ms[1].to_value("deg") == 0.0
    assert me[0].to_value("deg") == 1.3
    assert me[1].to_value("deg") == 0.0

    turn_speed = MODULE._resolve_turn_speed(prev, nxt)
    assert turn_speed.to_value("deg/s") == 0.5

    hint = MODULE._auto_turn_radius_hint(prev, nxt)
    # chord/3 = sqrt((1.3-1.1)^2 + (0.0-0.2)^2)/3 = sqrt(0.08)/3 ≈ 0.09428
    assert abs(float(hint) - ((0.2 ** 2 + 0.2 ** 2) ** 0.5) / 3.0) < 1e-9


def test_auto_turn_radius_hint_does_not_vectorize_tuple_quantities_with_numpy(monkeypatch):
    prev = _line(0, start=(0.0, 0.0), stop=(1.0, 0.0), speed=0.7, margin=0.3)
    nxt = _line(1, start=(1.0, 0.2), stop=(0.0, 0.2), speed=0.5, margin=0.1)

    orig = MODULE.np.asanyarray

    def guard(value, *args, **kwargs):
        if isinstance(value, tuple):
            raise AssertionError("_auto_turn_radius_hint must not pass tuple quantities to np.asanyarray")
        return orig(value, *args, **kwargs)

    monkeypatch.setattr(MODULE.np, "asanyarray", guard)
    hint = MODULE._auto_turn_radius_hint(prev, nxt)
    assert hint.to_value("deg") > 0.0


def test_build_scan_block_sections_optional_flags():
    lines = [_line(0), _line(1, start=(1.0, 0.2), stop=(0.0, 0.2))]
    sections = MODULE.build_scan_block_sections(
        lines,
        include_initial_standby=False,
        include_final_decelerate=False,
        include_final_standby=True,
        final_standby_duration=3.0 * MODULE.u.s,
    )
    assert [s.kind for s in sections] == [
        "accelerate",
        "line",
        "decelerate",
        "turn",
        "accelerate",
        "line",
        "final_standby",
    ]
    assert sections[-1].duration.to_value("s") == 3.0
    assert sections[-1].label == "L1:final_standby"




def test_curve_control_points_accept_dimensionless_direction_vectors_with_spatial_point_unit():
    p0, p1, p2, p3 = MODULE._curve_control_points(
        start=(q(0.0, "deg"), q(0.0, "deg")),
        stop=(q(1.0, "deg"), q(0.2, "deg")),
        entry_direction=(q(1.0), q(0.0)),
        exit_direction=(q(0.0), q(1.0)),
        turn_radius_hint=q(0.1, "deg"),
        unit="deg",
    )
    for point in (p0, p1, p2, p3):
        assert point.unit == MODULE.u.deg

def test_evaluate_curved_turn_kinematics_inferrs_spatial_unit_when_unit_is_none():
    kin = MODULE.evaluate_curved_turn_kinematics(
        start=(q(0.0), q(0.0)),
        stop=(q(1.0), q(0.2)),
        entry_direction=(q(1.0), q(0.0)),
        exit_direction=(q(0.0), q(1.0)),
        speed=q(0.5, "deg/s"),
        turn_radius_hint=q(0.1),
        unit=None,
    )
    assert kin["length"].unit == MODULE.u.deg
    assert kin["nominal_peak_speed"].unit == MODULE.u.deg / MODULE.u.s


def test_plan_scan_block_kinematics_handles_merged_turns_without_explicit_unit():
    lines = [
        _line(0, start=(0.0, 0.0), stop=(1.0, 0.0), speed=0.7, margin=0.3),
        _line(1, start=(1.0, 0.2), stop=(0.0, 0.2), speed=0.5, margin=0.1),
    ]
    report = MODULE.plan_scan_block_kinematics(lines)
    assert len(report["turns"]) == 1
    turn = report["turns"][0]
    assert turn["peak_speed"].unit == MODULE.u.deg / MODULE.u.s
    assert turn["peak_acceleration"].unit == MODULE.u.deg / MODULE.u.s**2