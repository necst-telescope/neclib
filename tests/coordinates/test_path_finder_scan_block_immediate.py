from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

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


def test_path_finder_scan_block_final_standby():
    pf = MODULE.PathFinder.__new__(MODULE.PathFinder)
    recorded = {}

    def fake_sequential(*args, repeat):
        recorded["args"] = args
        recorded["repeat"] = repeat
        if False:
            yield None

    pf.sequential = fake_sequential

    sections = [
        DummySection(kind="initial_standby", start=(0.0, 0.0), stop=(1.0, 0.0), speed=0.5, margin=0.1, label="L0:initial_standby", line_index=0, tight=False),
        DummySection(kind="accelerate", start=(0.0, 0.0), stop=(1.0, 0.0), speed=0.5, margin=0.1, label="L0:accelerate", line_index=0, tight=False),
        DummySection(kind="line", start=(0.0, 0.0), stop=(1.0, 0.0), speed=0.5, margin=0.1, label="L0", line_index=0, tight=True),
        DummySection(kind="decelerate", start=(0.0, 0.0), stop=(1.0, 0.0), speed=0.5, margin=0.1, label="L0:final_decelerate", line_index=0, tight=False),
        DummySection(kind="final_standby", start=(1.1, 0.0), duration=2.5, speed=0.5, label="L0:final_standby", line_index=0, tight=False),
    ]

    list(MODULE.PathFinder.scan_block(pf, scan_frame="altaz", sections=sections, unit="deg"))

    assert recorded["repeat"] == [-1, 1, 1, 1, 1]
    hold_ctor, hold_kwargs = recorded["args"][-1][0]
    assert hold_ctor == "Hold"
    assert hold_kwargs["point"] == (1.1, 0.0)
    assert hold_kwargs["frame"] == "altaz"
    assert hold_kwargs["duration"] == 2.5
