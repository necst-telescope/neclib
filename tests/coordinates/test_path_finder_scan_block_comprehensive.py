from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from tests._helpers.scan_block_stub_runtime import load_path_finder_module


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE = load_path_finder_module(REPO_ROOT)


class DummySection(SimpleNamespace):
    def __init__(self, **kwargs):
        defaults = dict(
            stop=None,
            speed=None,
            margin=None,
            duration=None,
            label="",
            line_index=-1,
            tight=False,
            turn_radius_hint=None,
        )
        defaults.update(kwargs)
        super().__init__(**defaults)


def _collect_paths(sections):
    pf = MODULE.PathFinder.__new__(MODULE.PathFinder)
    recorded = {}

    def fake_sequential(*args, repeat):
        recorded["args"] = args
        recorded["repeat"] = repeat
        if False:
            yield None

    pf.sequential = fake_sequential
    list(MODULE.PathFinder.scan_block(pf, scan_frame="altaz", sections=sections, unit="deg"))
    classes = [entry[0][0] for entry in recorded["args"]]
    return classes, recorded["repeat"]


def test_path_finder_scan_block_mixed_sequence_classes_and_repeats():
    sections = [
        DummySection(kind="initial_standby", start=(0.0, 0.0), stop=(1.0, 0.0), speed=0.5, margin=0.1),
        DummySection(kind="accelerate", start=(0.0, 0.0), stop=(1.0, 0.0), speed=0.5, margin=0.1),
        DummySection(kind="line", start=(0.0, 0.0), stop=(1.0, 0.0), speed=0.5, margin=0.1, tight=True),
        DummySection(kind="decelerate", start=(0.0, 0.0), stop=(1.0, 0.0), speed=0.5, margin=0.1),
        DummySection(kind="turn", start=(1.1, 0.0), stop=(-0.1, 0.2), speed=0.5, turn_radius_hint=0.1),
        DummySection(kind="accelerate", start=(1.0, 0.2), stop=(0.0, 0.2), speed=0.5, margin=0.1),
        DummySection(kind="line", start=(1.0, 0.2), stop=(0.0, 0.2), speed=0.5, margin=0.1, tight=True),
        DummySection(kind="final_decelerate", start=(1.0, 0.2), stop=(0.0, 0.2), speed=0.5, margin=0.1),
        DummySection(kind="final_standby", start=(-0.1, 0.2), duration=2.0),
    ]
    classes, repeats = _collect_paths(sections)
    assert classes == [
        "Standby", "ScanBlockAccelerate", "Linear", "Decelerate", "CurvedTurn",
        "ScanBlockAccelerate", "Linear", "Decelerate", "Hold",
    ]
    assert repeats == [-1, 1, 1, 1, 1, 1, 1, 1, 1]


def test_path_finder_scan_block_turn_without_neighbouring_line_raises():
    pf = MODULE.PathFinder.__new__(MODULE.PathFinder)
    pf.sequential = lambda *args, repeat: iter(())
    sections = [
        DummySection(kind="turn", start=(0.0, 0.0), stop=(1.0, 1.0), speed=0.5),
    ]
    with pytest.raises(ValueError, match="Cannot infer turn tangent"):
        list(MODULE.PathFinder.scan_block(pf, scan_frame="altaz", sections=sections, unit="deg"))


def test_path_finder_scan_block_final_standby_requires_duration():
    pf = MODULE.PathFinder.__new__(MODULE.PathFinder)
    pf.sequential = lambda *args, repeat: iter(())
    sections = [DummySection(kind="final_standby", start=(0.0, 0.0), duration=None)]
    with pytest.raises(ValueError, match="final_standby requires duration"):
        list(MODULE.PathFinder.scan_block(pf, scan_frame="altaz", sections=sections, unit="deg"))


def test_path_finder_scan_block_unsupported_kind_raises():
    pf = MODULE.PathFinder.__new__(MODULE.PathFinder)
    pf.sequential = lambda *args, repeat: iter(())
    sections = [DummySection(kind="weird_kind", start=(0.0, 0.0))]
    with pytest.raises(ValueError, match="Unsupported scan block section kind"):
        list(MODULE.PathFinder.scan_block(pf, scan_frame="altaz", sections=sections, unit="deg"))


def test_path_finder_scan_block_move_to_entry_maps_to_hold_waypoint_repeat_minus_one():
    sections = [
        DummySection(kind="move_to_entry", start=(-0.1, 0.0), stop=(-0.1, 0.0), duration=1.0, line_index=0, tight=False),
        DummySection(kind="accelerate", start=(0.0, 0.0), stop=(1.0, 0.0), speed=0.5, margin=0.1),
        DummySection(kind="line", start=(0.0, 0.0), stop=(1.0, 0.0), speed=0.5, margin=0.1, tight=True),
    ]
    classes, repeats = _collect_paths(sections)
    assert classes[:3] == ["Hold", "ScanBlockAccelerate", "Linear"]
    assert repeats[:3] == [-1, 1, 1]
