from __future__ import annotations

from pathlib import Path

from tests._helpers.scan_block_stub_runtime import load_scan_block_module, q


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE = load_scan_block_module(REPO_ROOT)


def test_build_scan_block_sections_inserts_curved_turn_between_two_lines():
    lines = [
        MODULE.ScanBlockLine(
            start=(q(0.0), q(0.0)),
            stop=(q(1.0), q(0.0)),
            speed=q(0.5, "deg/s"),
            margin=q(0.1),
            label="line0",
            line_index=0,
        ),
        MODULE.ScanBlockLine(
            start=(q(1.0), q(0.2)),
            stop=(q(0.0), q(0.2)),
            speed=q(0.5, "deg/s"),
            margin=q(0.1),
            label="line1",
            line_index=1,
        ),
    ]
    sections = MODULE.build_scan_block_sections(lines)
    kinds = [section.kind for section in sections]
    assert kinds == [
        "initial_standby",
        "accelerate",
        "line",
        "turn",
        "line",
        "decelerate",
    ]
    turn = sections[3]
    assert turn.turn_radius_hint is not None
    assert float(turn.turn_radius_hint) > 0


def test_single_line_handoff_sections_use_handoff_turn_and_standby():
    line = MODULE.ScanBlockLine(
        start=(q(0.0), q(0.0)),
        stop=(q(1.0), q(0.0)),
        speed=q(0.5, "deg/s"),
        margin=q(0.1),
        label="line0",
        line_index=0,
    )
    nxt = MODULE.ScanBlockLine(
        start=(q(1.0), q(0.2)),
        stop=(q(0.0), q(0.2)),
        speed=q(0.5, "deg/s"),
        margin=q(0.1),
        label="line1",
        line_index=1,
    )
    sections = MODULE.build_scan_block_sections([line], include_initial_standby=False, next_entry_line=nxt)
    assert [section.kind for section in sections] == ["accelerate", "line", "decelerate", "handoff_turn", "handoff_standby"]


def test_hold_constructor_accepts_duration_without_rest_to_rest_nameerror():
    class DummyCalc:
        command_freq = 10.0

    hold = MODULE.Hold(
        DummyCalc(),
        point=(q(1.0), q(-2.0)),
        frame="altaz",
        duration=q(2.5, "s"),
        unit="deg",
    )

    assert hold.n_cmd == 25
