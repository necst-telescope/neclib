from typing import Generator

import astropy.units as u
import numpy as np

from .observation_spec_base import (
    ObservationMode,
    ObservationSpec,
    TimeKeeper,
    Waypoint,
)


class OTFSpec(ObservationSpec):
    __slots__ = ("_hot_time_keeper", "_off_time_keeper")

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self._hot_time_keeper = TimeKeeper(self["load_interval"])
        self._off_time_keeper = TimeKeeper(self["off_interval"])

    def observe(self) -> Generator[Waypoint, None, None]:
        for i, coord in enumerate(self._scan()):
            if self._hot_time_keeper.should_observe:
                self._hot_time_keeper.tell_observed()
                yield self.hot(f"{i}")

            if self._off_time_keeper.should_observe:
                self._off_time_keeper.tell_observed()
                yield self.off(f"{i}")

            self._hot_time_keeper.increment("scan")
            self._off_time_keeper.increment("scan")
            coord.id = f"{i}"
            yield coord

        # Should be executed at the end of the observation, to enable interpolation.
        yield self.hot("9999")
        yield self.off("9999")

    def _scan(self) -> Generator[Waypoint, None, None]:
        scan_length = self["scan_length"] * self["scan_velocity"]
        pa = self["position_angle"]
        _start_x, _start_y = self["start_position_x"], self["start_position_y"]
        start_x = _start_x * np.cos(pa) - _start_y * np.sin(pa)
        start_y = _start_x * np.sin(pa) + _start_y * np.cos(pa)
        for idx in range(int(self["first_scan"]), int(self["n"])):
            if self["scan_direction"].upper() == "X":
                offset = (0 * u.deg, idx * self["scan_spacing"])
            else:
                offset = (idx * self["scan_spacing"], 0 * u.deg)

            # Position angle correction
            offset = (
                offset[0] * np.cos(pa) - offset[1] * np.sin(pa),
                offset[0] * np.sin(pa) + offset[1] * np.cos(pa),
            )

            start = (start_x + offset[0], start_y + offset[1])
            stop = (
                start[0] + scan_length * np.cos(pa),
                start[1] + scan_length * np.sin(pa),
            )

            yield Waypoint(
                mode=ObservationMode.ON,
                reference=self._reference,
                start=start,
                stop=stop,
                speed=abs(self["scan_velocity"]),
                scan_frame=self["coord_sys"],
            )
