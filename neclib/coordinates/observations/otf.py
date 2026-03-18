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

    @staticmethod
    def _rotate_xy(
        x: u.Quantity, y: u.Quantity, angle: u.Quantity
    ) -> tuple[u.Quantity, u.Quantity]:
        """
        Rotate (x, y) in the scan plane by ``angle`` (counter-clockwise).

        This is a 2D rotation in the tangent-plane coordinates used by this OTF spec.
        Returned units follow x/y.
        """
        xr = x * np.cos(angle) - y * np.sin(angle)
        yr = x * np.sin(angle) + y * np.cos(angle)
        return xr, yr

    def _scan(self) -> Generator[Waypoint, None, None]:
        # Semantics:
        # - position_angle:
        #   rotation of the scan-plane axes (X', Y') relative to coord_sys axes.
        # - scan_direction: choose the along-scan axis in that scan-plane ("X" or "Y").
        #
        # scan_direction == "X":
        #   along-scan  : +X'
        #   cross-scan  : +Y' (scan_spacing steps)
        #
        # scan_direction == "Y":
        #   along-scan  : +Y'
        #   cross-scan  : +X' (scan_spacing steps)
        #
        # After defining start/stop in (X', Y'), we rotate them by position_angle.

        scan_length = self["scan_length"] * self["scan_velocity"]
        pa = self["position_angle"]

        # Start position in the *unrotated* scan-plane coordinates (X', Y')
        start0_x = self["start_position_x"]
        start0_y = self["start_position_y"]

        sd = str(self["scan_direction"]).strip().upper()
        if sd not in ("X", "Y"):
            raise ValueError(
                "scan_direction must be 'X' or 'Y' (case-insensitive)"
                "got: {self['scan_direction']!r}"
            )

        first_scan = int(self["first_scan"])
        n_scan = int(self["n"])
        spacing = self["scan_spacing"]
        zero = 0 * spacing  # keep unit consistent with scan_spacing

        for idx in range(first_scan, n_scan):
            if sd == "X":
                # Scan along X' and step rows along Y'
                cross_offset_x = zero
                cross_offset_y = idx * spacing
                along_dx = scan_length
                along_dy = 0 * u.deg
            else:
                # Scan along Y' and step rows along X'
                cross_offset_x = idx * spacing
                cross_offset_y = zero
                along_dx = 0 * u.deg
                along_dy = scan_length

            # Start/stop in scan-plane (before rotation)
            start_scan_x = start0_x + cross_offset_x
            start_scan_y = start0_y + cross_offset_y
            stop_scan_x = start_scan_x + along_dx
            stop_scan_y = start_scan_y + along_dy

            # Rotate into coord_sys axes
            start_x, start_y = self._rotate_xy(start_scan_x, start_scan_y, pa)
            stop_x, stop_y = self._rotate_xy(stop_scan_x, stop_scan_y, pa)

            yield Waypoint(
                mode=ObservationMode.ON,
                reference=self._reference,
                start=(start_x, start_y),
                stop=(stop_x, stop_y),
                speed=abs(self["scan_velocity"]),
                scan_frame=self["coord_sys"],
            )
