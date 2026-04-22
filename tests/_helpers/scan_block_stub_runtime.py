from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from typing import Iterable

import numpy as np


class FakeUnit:
    def __init__(self, name: str):
        self.name = name

    def __rmul__(self, value):
        return FakeQuantity(value, self.name)

    def __mul__(self, value):
        return FakeQuantity(value, self.name)

    def __truediv__(self, other):
        other_name = getattr(other, 'name', str(other))
        return FakeUnit(f"{self.name}/{other_name}")

    def __repr__(self):
        return self.name


class FakeQuantity(np.ndarray):
    __array_priority__ = 1000

    def __new__(cls, value=0.0, unit: str = ""):
        obj = np.asarray(value, dtype=float).view(cls)
        obj.unit = unit
        return obj

    def __array_finalize__(self, obj):
        self.unit = getattr(obj, 'unit', '')

    def to_value(self, unit=None):
        arr = np.asarray(self)
        if arr.shape == ():
            return float(arr)
        return arr.astype(float)

    def to(self, unit=None):
        return FakeQuantity(np.asarray(self), getattr(unit, "name", unit) or self.unit)

    def decompose(self):
        return self

    def __getitem__(self, item):
        out = super().__getitem__(item)
        if isinstance(out, np.ndarray):
            return out.view(FakeQuantity)
        return FakeQuantity(out, self.unit)

    def __mul__(self, other):
        if isinstance(other, FakeUnit):
            return FakeQuantity(np.asarray(self), f"{self.unit}*{other.name}")
        return super().__mul__(other)

    def __truediv__(self, other):
        if isinstance(other, FakeUnit):
            return FakeQuantity(np.asarray(self), f"{self.unit}/{other.name}")
        return super().__truediv__(other)


def q(value: float, unit: str = "deg") -> FakeQuantity:
    return FakeQuantity(value, unit)


def clear_modules(prefixes: Iterable[str]) -> None:
    prefixes = tuple(prefixes)
    for name in list(sys.modules):
        if name.startswith(prefixes):
            del sys.modules[name]


def _load_source(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def install_astropy_stub() -> None:
    astropy = types.ModuleType("astropy")
    astropy.__path__ = []
    units = types.ModuleType("astropy.units")
    units.Quantity = FakeQuantity
    units.Unit = FakeUnit
    units.deg = FakeUnit("deg")
    units.s = FakeUnit("s")
    units.GHz = FakeUnit("GHz")
    units.dimensionless_unscaled = FakeUnit("")
    sys.modules["astropy"] = astropy
    sys.modules["astropy.units"] = units


def load_path_finder_module(repo_root: Path):
    clear_modules(["neclib", "astropy"])
    install_astropy_stub()

    neclib = types.ModuleType("neclib")
    neclib.__path__ = []
    sys.modules["neclib"] = neclib

    core = types.ModuleType("neclib.core")
    core.__path__ = []
    core.config = types.SimpleNamespace(
        antenna_max_speed=types.SimpleNamespace(az=q(1.6, "deg/s"), el=q(1.6, "deg/s")),
        antenna_max_acceleration=types.SimpleNamespace(az=q(1.6, "deg/s^2"), el=q(1.6, "deg/s^2")),
    )
    core.get_logger = lambda *a, **k: types.SimpleNamespace(info=lambda *a, **k: None, warning=lambda *a, **k: None)
    sys.modules["neclib.core"] = core

    core_types = types.ModuleType("neclib.core.types")
    core_types.CoordFrameType = str
    core_types.DimensionLess = float
    core_types.UnitType = str
    sys.modules["neclib.core.types"] = core_types

    coordinates = types.ModuleType("neclib.coordinates")
    coordinates.__path__ = []
    sys.modules["neclib.coordinates"] = coordinates

    convert = types.ModuleType("neclib.coordinates.convert")
    class CoordCalculator:
        pass
    convert.CoordCalculator = CoordCalculator
    sys.modules["neclib.coordinates.convert"] = convert

    paths = types.ModuleType("neclib.coordinates.paths")

    class ControlContext:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class Index:
        def __init__(self, index=None, time=None):
            self.index = index
            self.time = time

    class _BasePath:
        def __init__(self, *args, **kwargs):
            self.arguments = ((self.__class__.__name__, kwargs), {})

    class Standby(_BasePath):
        pass
    class Accelerate(_BasePath):
        pass
    class ScanBlockAccelerate(_BasePath):
        pass
    class Linear(_BasePath):
        pass
    class Decelerate(_BasePath):
        pass
    class CurvedTurn(_BasePath):
        pass
    class Hold(_BasePath):
        pass
    class Track(_BasePath):
        pass

    class ScanBlockSection:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    paths.ControlContext = ControlContext
    paths.Index = Index
    paths.Standby = Standby
    paths.Accelerate = Accelerate
    paths.ScanBlockAccelerate = ScanBlockAccelerate
    paths.Linear = Linear
    paths.Decelerate = Decelerate
    paths.CurvedTurn = CurvedTurn
    paths.Hold = Hold
    paths.Track = Track
    paths.ScanBlockSection = ScanBlockSection
    sys.modules["neclib.coordinates.paths"] = paths

    return _load_source(
        "neclib.coordinates.path_finder",
        repo_root / "neclib-main" / "neclib" / "coordinates" / "path_finder.py",
    )



def load_scan_block_module(repo_root: Path):
    clear_modules(["neclib", "astropy"])
    install_astropy_stub()

    neclib = types.ModuleType("neclib")
    neclib.__path__ = []
    sys.modules["neclib"] = neclib

    core = types.ModuleType("neclib.core")
    core.__path__ = []
    core.config = types.SimpleNamespace(
        antenna_max_speed=types.SimpleNamespace(az=q(1.6, "deg/s"), el=q(1.6, "deg/s")),
        antenna_max_acceleration=types.SimpleNamespace(az=q(1.6, "deg/s^2"), el=q(1.6, "deg/s^2")),
    )
    core.get_logger = lambda *a, **k: types.SimpleNamespace(info=lambda *a, **k: None, warning=lambda *a, **k: None)
    sys.modules["neclib.core"] = core

    core_types = types.ModuleType("neclib.core.types")
    core_types.CoordFrameType = str
    core_types.DimensionLess = float
    core_types.UnitType = str
    sys.modules["neclib.core.types"] = core_types

    core_norm = types.ModuleType("neclib.core.normalization")
    def get_quantity(value, unit=None):
        if isinstance(value, FakeQuantity):
            qv = value
            if unit is not None:
                return FakeQuantity(qv.to_value(unit), unit)
            return qv
        if isinstance(value, (tuple, list, np.ndarray)):
            if len(value) == 0:
                return FakeQuantity([], unit or "")
            out_unit = unit or getattr(value[0], 'unit', '')
            vals = [
                float(v.to_value(out_unit)) if hasattr(v, 'to_value') else float(v)
                for v in value
            ]
            return FakeQuantity(vals, out_unit)
        out_unit = unit or getattr(value, 'unit', '')
        if hasattr(value, 'to_value'):
            value = value.to_value(out_unit)
        return FakeQuantity(float(value), out_unit)
    core_norm.get_quantity = get_quantity
    sys.modules["neclib.core.normalization"] = core_norm

    coordinates = types.ModuleType("neclib.coordinates")
    coordinates.__path__ = []
    sys.modules["neclib.coordinates"] = coordinates

    paths_pkg = types.ModuleType("neclib.coordinates.paths")
    paths_pkg.__path__ = []
    sys.modules["neclib.coordinates.paths"] = paths_pkg

    linear = types.ModuleType("neclib.coordinates.paths.linear")
    class _Path:
        def __init__(self, calc=None, *target, unit=None, **kwargs):
            self._calc = calc
            self._target = target[0] if target else None
            self._unit = unit
    class Linear(_Path):
        pass
    class Accelerate(Linear):
        pass
    class Standby(Linear):
        pass
    linear.Linear = Linear
    linear.Accelerate = Accelerate
    linear.Standby = Standby
    sys.modules["neclib.coordinates.paths.linear"] = linear

    path_base = types.ModuleType("neclib.coordinates.paths.path_base")
    class ControlContext:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    class Index:
        def __init__(self, index=None, time=None):
            self.index = index
            self.time = time
    class Path(_Path):
        pass
    path_base.ControlContext = ControlContext
    path_base.Index = Index
    path_base.Path = Path
    sys.modules["neclib.coordinates.paths.path_base"] = path_base

    module = _load_source(
        "neclib.coordinates.paths.scan_block",
        repo_root / "neclib-main" / "neclib" / "coordinates" / "paths" / "scan_block.py",
    )

    _orig_norm = np.linalg.norm

    def _quantity_norm(arr, *args, **kwargs):
        axis = kwargs.get("axis", None)
        if isinstance(arr, FakeQuantity):
            unit = getattr(arr, 'unit', '')
            out = _orig_norm(np.asarray(arr, dtype=float), *args, **kwargs)
            return FakeQuantity(out, unit)
        return _orig_norm(arr, *args, **kwargs)

    module.np.linalg.norm = _quantity_norm
    return module
