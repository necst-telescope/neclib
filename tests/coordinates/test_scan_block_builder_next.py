from __future__ import annotations

from pathlib import Path

from tests._helpers.scan_block_stub_runtime import load_scan_block_module, q


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE = load_scan_block_module(REPO_ROOT)


def _line(idx, y, *, label=None):
    return MODULE.ScanBlockLine(
        start=(q(0.0), q(y)),
        stop=(q(1.0), q(y)),
        speed=q(0.5, "deg/s"),
        margin=q(0.1),
        label=label or f"L{idx}",
        line_index=idx,
    )


def test_build_scan_block_sections_single_line():
    line = _line(7, 0.0, label="SCI")
    sections = MODULE.build_scan_block_sections([line])

    assert [s.kind for s in sections] == [
        "initial_standby",
        "accelerate",
        "line",
        "decelerate",
    ]
    assert [s.tight for s in sections] == [False, False, True, False]
    assert [s.label for s in sections] == [
        "SCI:initial_standby",
        "SCI:accelerate",
        "SCI",
        "SCI:final_decelerate",
    ]
    assert all(s.line_index == 7 for s in sections)
    assert sections[0].start == line.start
    assert sections[0].stop == line.stop
    assert sections[-1].margin.to_value("deg") == 0.1


def test_build_scan_block_sections_three_lines_with_final_standby():
    lines = [_line(0, 0.0), _line(1, 0.2), _line(2, 0.4)]
    sections = MODULE.build_scan_block_sections(
        lines,
        include_initial_standby=True,
        include_final_decelerate=True,
        include_final_standby=True,
        final_standby_duration=2.5 * MODULE.u.s,
    )

    assert [s.kind for s in sections] == [
        "initial_standby",
        "accelerate", "line", "decelerate", "turn",
        "accelerate", "line", "decelerate", "turn",
        "accelerate", "line", "decelerate", "final_standby",
    ]
    turn1, turn2 = sections[4], sections[8]
    assert turn1.label == "turn:0->1"
    assert turn1.line_index == 1
    assert turn1.turn_radius_hint.to_value("deg") > 0.0
    assert turn2.label == "turn:1->2"
    assert turn2.line_index == 2

    final_standby = sections[-1]
    expected = MODULE.margin_stop_of(lines[-1])
    assert final_standby.label == "L2:final_standby"
    assert final_standby.line_index == 2
    assert final_standby.duration.to_value("s") == 2.5
    assert final_standby.start[0].to_value("deg") == expected[0].to_value("deg")
    assert final_standby.start[1].to_value("deg") == expected[1].to_value("deg")
