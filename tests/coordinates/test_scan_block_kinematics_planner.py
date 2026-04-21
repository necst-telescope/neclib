from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from tests._helpers.scan_block_stub_runtime import load_scan_block_module, q

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE = load_scan_block_module(REPO_ROOT)


class DummyCalc:
    command_freq = 50.0

    def coordinate_delta(self, *args, **kwargs):
        return None


def _line(start, stop, speed=0.5, margin=0.1, label="L", line_index=0):
    return MODULE.ScanBlockLine(
        start=(q(start[0]), q(start[1])),
        stop=(q(stop[0]), q(stop[1])),
        speed=q(speed, "deg/s"),
        margin=q(margin),
        label=label,
        line_index=line_index,
    )




def test_conservative_limits_use_provisional_jerk_when_explicit_limit_is_missing():
    limits = MODULE.conservative_antenna_kinematic_limits()
    assert limits.max_jerk is not None
    assert abs(limits.max_jerk.to_value("deg/s^3") - 16.0) < 1e-9


def test_provisional_jerk_scales_with_command_frequency():
    old = getattr(MODULE.config, "antenna_command_frequency", None)
    MODULE.config.antenna_command_frequency = 100.0
    try:
        limits = MODULE.conservative_antenna_kinematic_limits()
        assert abs(limits.max_jerk.to_value("deg/s^3") - 16.0) < 1e-9
        MODULE.config.antenna_command_frequency = 10.0
        limits = MODULE.conservative_antenna_kinematic_limits()
        assert abs(limits.max_jerk.to_value("deg/s^3") - 3.2) < 1e-9
    finally:
        if old is None:
            delattr(MODULE.config, "antenna_command_frequency")
        else:
            MODULE.config.antenna_command_frequency = old

def test_single_line_required_acceleration_matches_edge_profile_nominal_peak():
    line = _line((0.0, 0.0), (1.0, 0.0), speed=0.5, margin=0.1)
    required = MODULE.single_line_required_acceleration(line)
    assert abs(required.to_value("deg/s^2") - 2.34375) < 1e-6


def test_single_line_edge_planner_stretches_duration_to_respect_conservative_limits():
    kin = MODULE.evaluate_single_line_edge_kinematics(
        speed=q(0.7, "deg/s"),
        margin=q(0.1),
        unit="deg",
        limits=MODULE.conservative_antenna_kinematic_limits(),
    )
    assert kin["duration"].to_value("s") > kin["nominal_duration"].to_value("s")
    assert kin["peak_acceleration"].to_value("deg/s^2") <= 1.6 + 1e-6


def test_curved_turn_planner_stretches_duration_to_respect_conservative_limits():
    kin = MODULE.evaluate_curved_turn_kinematics(
        start=(q(1.1), q(0.0)),
        stop=(q(-0.1), q(0.2)),
        entry_direction=(q(1.0), q(0.0)),
        exit_direction=(q(-1.0), q(0.0)),
        speed=q(0.5, "deg/s"),
        turn_radius_hint=q(0.1),
        unit="deg",
        limits=MODULE.conservative_antenna_kinematic_limits(),
        samples=2001,
    )
    assert kin["duration"].to_value("s") > kin["nominal_duration"].to_value("s")
    assert kin["peak_speed"].to_value("deg/s") <= 1.6 + 1e-9
    assert kin["peak_acceleration"].to_value("deg/s^2") <= 1.6 + 1e-9


def test_curved_turn_n_cmd_uses_limited_duration_not_nominal_average_speed_only():
    turn = MODULE.CurvedTurn(
        DummyCalc(),
        unit="deg",
        start=(q(1.1), q(0.0)),
        stop=(q(-0.1), q(0.2)),
        scan_frame="altaz",
        entry_direction=(q(1.0), q(0.0)),
        exit_direction=(q(-1.0), q(0.0)),
        speed=q(0.5, "deg/s"),
        turn_radius_hint=q(0.1),
    )
    kin = MODULE.evaluate_curved_turn_kinematics(
        start=(q(1.1), q(0.0)),
        stop=(q(-0.1), q(0.2)),
        entry_direction=(q(1.0), q(0.0)),
        exit_direction=(q(-1.0), q(0.0)),
        speed=q(0.5, "deg/s"),
        turn_radius_hint=q(0.1),
        unit="deg",
        limits=MODULE.conservative_antenna_kinematic_limits(),
        samples=2001,
    )
    expected = int(round(kin["duration"].to_value("s") * DummyCalc.command_freq))
    assert turn.n_cmd >= expected


def test_plan_scan_block_kinematics_slows_single_line_and_turn_to_stay_safe():
    lines = [
        _line((0.0, 0.0), (1.0, 0.0), speed=0.7, margin=0.1, label="A", line_index=0),
        _line((1.0, 0.2), (0.0, 0.2), speed=0.5, margin=0.1, label="B", line_index=1),
    ]
    report = MODULE.plan_scan_block_kinematics(lines, samples=2001)
    assert report["lines"][0]["within_limits"] is True
    assert report["lines"][0]["duration_scale"].to_value("") > 1.0
    assert report["turns"][0]["within_speed_limit"] is True
    assert report["turns"][0]["within_acceleration_limit"] is True
    assert report["turns"][0]["duration_scale"].to_value("") > 1.0


def test_curved_turn_planner_can_use_explicit_jerk_limit():
    limits = MODULE.ScanBlockKinematicLimits(
        max_speed=q(10.0, "deg/s"),
        max_acceleration=q(10.0, "deg/s^2"),
        max_jerk=q(1.0, "deg/s^3"),
    )
    kin = MODULE.evaluate_curved_turn_kinematics(
        start=(q(1.1), q(0.0)),
        stop=(q(-0.1), q(0.2)),
        entry_direction=(q(1.0), q(0.0)),
        exit_direction=(q(-1.0), q(0.0)),
        speed=q(0.5, "deg/s"),
        turn_radius_hint=q(0.1),
        unit="deg",
        limits=limits,
        samples=2001,
    )
    assert kin["duration"].to_value("s") > kin["nominal_duration"].to_value("s")
    assert kin["jerk_scale"].to_value("") >= 1.0
    assert kin["peak_jerk"].to_value("deg/s^3") <= 1.0 + 1e-6


def test_curved_turn_time_law_reports_continuous_speed_for_interior_turns():
    kin = MODULE.evaluate_curved_turn_kinematics(
        start=(q(1.1), q(0.0)),
        stop=(q(-0.1), q(0.2)),
        entry_direction=(q(1.0), q(0.0)),
        exit_direction=(q(-1.0), q(0.0)),
        speed=q(0.5, "deg/s"),
        turn_radius_hint=q(0.1),
        unit="deg",
        limits=None,
        samples=2001,
    )
    assert kin["time_law"] == "cubic_bezier_continuous_speed"
    assert kin["nominal_peak_speed"].to_value("deg/s") >= 0.5


def test_rest_to_rest_curved_turn_still_reports_legacy_time_law():
    kin = MODULE.evaluate_curved_turn_kinematics(
        start=(q(1.1), q(0.0)),
        stop=(q(-0.1), q(0.2)),
        entry_direction=(q(1.0), q(0.0)),
        exit_direction=(q(-1.0), q(0.0)),
        speed=q(0.5, "deg/s"),
        turn_radius_hint=q(0.1),
        unit="deg",
        limits=None,
        samples=2001,
        rest_to_rest=True,
    )
    assert kin["time_law"] == "smoothstep7"
    assert kin["nominal_peak_jerk"].to_value("deg/s^3") > 0.0


def test_curve_control_points_accept_dimensionless_directions_with_spatial_unit():
    p0, p1, p2, p3 = MODULE._curve_control_points(
        start=(q(1.1), q(0.0)),
        stop=(q(-0.1), q(0.2)),
        entry_direction=(q(1.0, ""), q(0.0, "")),
        exit_direction=(q(-1.0, ""), q(0.0, "")),
        turn_radius_hint=q(0.1),
        unit="deg",
    )
    for p in (p0, p1, p2, p3):
        assert getattr(p, "unit", None) == "deg"


def test_plan_scan_block_kinematics_reports_turn_jerk_limit_without_unit_mismatch():
    lines = [
        _line((0.0, 0.0), (1.0, 0.0), speed=0.7, margin=0.1, label="A", line_index=0),
        _line((1.0, 0.2), (0.0, 0.2), speed=0.5, margin=0.1, label="B", line_index=1),
    ]
    report = MODULE.plan_scan_block_kinematics(lines, samples=2001)
    assert report["turns"][0]["within_jerk_limit"] in (True, False, None)
    assert report["turns"][0]["peak_jerk"].to_value("deg/s^3") >= 0.0


def test_curved_turn_constructor_accepts_dimensionless_directions_and_quantity_speed_without_unit():
    turn = MODULE.CurvedTurn(
        DummyCalc(),
        start=(q(1.1), q(0.0)),
        stop=(q(-0.1), q(0.2)),
        scan_frame="altaz",
        entry_direction=(q(1.0, ""), q(0.0, "")),
        exit_direction=(q(-1.0, ""), q(0.0, "")),
        speed=q(0.5, "deg/s"),
        turn_radius_hint=q(0.1),
    )
    assert str(turn._start.unit) == "deg"
    assert str(turn._entry_direction.unit) == ""
    assert str(turn._speed.unit) in ("deg / s", "deg/s")
    assert turn.n_cmd > 0


def test_rest_to_rest_curved_turn_constructor_still_supports_quantity_directions():
    turn = MODULE.CurvedTurn(
        DummyCalc(),
        start=(q(1.1), q(0.0)),
        stop=(q(-0.1), q(0.2)),
        scan_frame="altaz",
        entry_direction=(q(1.0, ""), q(0.0, "")),
        exit_direction=(q(-1.0, ""), q(0.0, "")),
        speed=q(0.5, "deg/s"),
        turn_radius_hint=q(0.1),
        rest_to_rest=True,
    )
    assert turn.n_cmd > 0
