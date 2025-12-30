from itertools import count
from typing import Generator
from .observation_spec_base import (
    ObservationMode,
    ObservationSpec,
    TimeKeeper,
    Waypoint,
)


class PSWSpec(ObservationSpec):
    __slots__ = ("_hot_time_keeper", "_off_time_keeper")
    _repr_frame = "altaz"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        # Cannot define this in scan mode, so use default value of 1 in such case.
        self._hot_time_keeper = TimeKeeper(self["load_interval"])
        self._off_time_keeper = TimeKeeper(self["off_interval"])

    def observe(self) -> Generator[Waypoint, None, None]:
        iterate_counter = count() if self["n"] < 0 else range(self["n"])
        for iteration_count in iterate_counter:
            coords = self._points()
            unit = "point"

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
        )

    def _points(self) -> Generator[Waypoint, None, None]:
        n = self["n"]
        print(n)
        if n < 0:
            raise ValueError("n must be positive.")
        on_point = self._on_point.reference
        # for idx in range(0, n):
        yield Waypoint(
            mode=ObservationMode.ON,
            reference=on_point,
            integration=self["integ_on"],
        )
