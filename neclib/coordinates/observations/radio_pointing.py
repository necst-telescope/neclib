from itertools import count
from typing import Generator

import astropy.units as u

from .observation_spec_base import (
    ObservationMode,
    ObservationSpec,
    TimeKeeper,
    Waypoint,
)


class RadioPointingSpec(ObservationSpec):
    __slots__ = ("_hot_time_keeper", "_off_time_keeper")
    _repr_frame = "altaz"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        # Cannot define this in scan mode, so use default value of 1 in such case.
        _points_per_scan = max(1, (self["method"] + 1) / 2)

        self._hot_time_keeper = TimeKeeper(self["load_interval"], _points_per_scan)
        self._off_time_keeper = TimeKeeper(self["off_interval"], _points_per_scan)

    def observe(self) -> Generator[Waypoint, None, None]:
        iterate_counter = count() if self["n"] < 0 else range(self["n"])
        _method = self["method"]

        for iteration_count in iterate_counter:
            coords = self._points() if _method > 0 else self._scan()
            unit = "point" if _method > 0 else "scan"

            for i, coord in enumerate(coords):
                if self._hot_time_keeper.should_observe:
                    self._hot_time_keeper.tell_observed()
                    yield self.hot(f"{iteration_count}-{i}")

                if self._off_time_keeper.should_observe:
                    self._off_time_keeper.tell_observed()
                    yield self.off(f"{iteration_count}-{i}")

                self._hot_time_keeper.increment(unit)
                self._off_time_keeper.increment(unit)
                coord.id = f"{iteration_count}-{i}"
                yield coord

        # Should be executed at the end of the observation, to enable interpolation.
        yield self.hot("9999")
        yield self.off("9999")

    @property
    def _on_point(self) -> Waypoint:
        return Waypoint(
            mode=ObservationMode.ON,
            reference=self._reference,
            integration=self["integ_on"],
            offset=(self["offset_az"], self["offset_el"], "altaz"),
        )

    def _points(self) -> Generator[Waypoint, None, None]:
        n = self["n"]
        if (n > 0) and (n % 4 != 1):
            raise ValueError("n must be positive and 1 + 4 * N.")

        on_point = self._on_point.reference

        n_points_per_arm = int((self["method"] - 1) / 4)
        for idx in range(-1 * n_points_per_arm, n_points_per_arm + 1):
            offset = (
                self["offset_az"] + self["grid_az"] * idx,
                self["offset_el"],
                "altaz",
            )
            yield Waypoint(
                mode=ObservationMode.ON,
                reference=on_point,
                offset=offset,
                integration=self["integ_on"],
            )
        for idx in range(-1 * n_points_per_arm, n_points_per_arm + 1):
            offset = (
                self["offset_az"],
                self["offset_el"] + self["grid_el"] * idx,
                "altaz",
            )
            yield Waypoint(
                mode=ObservationMode.ON,
                reference=on_point,
                offset=offset,
                integration=self["integ_on"],
            )

    def _scan(self) -> Generator[Waypoint, None, None]:
        yield Waypoint(
            mode=ObservationMode.ON,
            start=(-1 * self["max_separation_az"], 0 << u.deg),
            stop=(self["max_separation_az"], 0 << u.deg),
            reference=self._reference,
            scan_frame="altaz",
            speed=self["speed"],
            offset=(self["offset_az"], self["offset_el"], "altaz"),
        )
        yield Waypoint(
            mode=ObservationMode.ON,
            start=(0 << u.deg, self["max_separation_el"]),
            stop=(0 << u.deg, -1 * self["max_separation_el"]),
            reference=self._reference,
            scan_frame="altaz",
            speed=self["speed"],
            offset=(self["offset_az"], self["offset_el"], "altaz"),
        )
