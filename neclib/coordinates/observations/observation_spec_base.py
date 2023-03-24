import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Generator, Iterator, Optional, Tuple, Union

import astropy.units as u
import matplotlib.pyplot as plt
import pandas as pd
from astropy.coordinates import SkyCoord

from ...core import Parameters
from ...core.formatting import html_repr_of_observation_spec
from ...core.types import CoordFrameType, CoordinateType, UnitType
from ...core.units import scan_to_points


class ObservationMode(Enum):
    """Type of observation to be performed at certain coordinate."""

    DRIVE = "#777"
    ON = "#0F5"
    OFF = "#0DF"
    HOT = "#F50"
    SKY = "#0DF"


class TimeKeeper:
    """Judge whether it's time to run constant interval observation or not."""

    def __init__(self, interval: u.Quantity, points_per_scan: int = 1):
        self.interval = interval
        self.last = None
        if self._time_based:
            self.count = 0
        else:
            self.count = u.Quantity(0, self.interval.unit)
        self.points_per_scan = points_per_scan

    @property
    def should_observe(self) -> bool:
        """Return ``True`` if it's time to run observation, otherwise ``False``."""
        if self._time_based:
            self.count = time.time() * u.s
        if self.last is None:
            return True
        return bool((self.count - self.last) >= self.interval)

    @property
    def _time_based(self) -> bool:
        return self.interval.unit.is_equivalent(u.s)

    def increment(self, unit: UnitType) -> None:
        """Increment the counter, which will be compared with ``interval``."""
        if not self._time_based:
            _unity = u.Quantity(1, unit or self.interval.unit)
            unity = _unity.to(
                self.interval.unit, equivalencies=scan_to_points(self.points_per_scan)
            )
            self.count = self.count + unity

    def tell_observed(self) -> None:
        """Tell the time keeper that the observation has been completed."""
        self.last = time.time() * u.s if self._time_based else self.count


@dataclass
class Waypoint:
    mode: ObservationMode
    """Observation mode."""
    target: Optional[Union[str, CoordinateType]] = None
    """Coordinate or name of the target object."""
    reference: Optional[Union[str, CoordinateType]] = None
    """Coordinate or name of the object the other coordinate is defined relative to."""
    scan_frame: Optional[CoordFrameType] = None
    """Coordinate frame in which the scan is performed."""
    start: Optional[Tuple[u.Quantity, u.Quantity]] = None
    """Start position of the scan. The frame is defined in ``scan_frame``."""
    stop: Optional[Tuple[u.Quantity, u.Quantity]] = None
    """Stop position of the scan. The frame is defined in ``scan_frame``."""
    offset: Optional[CoordinateType] = None
    """Offset applied to all the coordinates specified above."""
    speed: Optional[u.Quantity] = None
    """Scan speed."""
    integration: Optional[u.Quantity] = None
    """Integration time."""
    id: Any = None
    """Identifier of the coordinate, if necessary."""

    @property
    def is_scan(self) -> bool:
        """Whether this coordinate contains enough information to perform a scan."""
        params = (self.start, self.stop, self.speed, self.scan_frame)
        return all(x is not None for x in params)

    @property
    def with_offset(self) -> bool:
        """Whether this coordinate should be offset by certain amount."""
        return self.offset is not None

    @property
    def name_query(self) -> bool:
        """Whether the target is specified by its name."""
        return isinstance(self.target, str) or isinstance(self.reference, str)

    @property
    def coordinates(self) -> SkyCoord:
        """Return a list of coordinates this section represents.

        Warning
        -------
        This property doesn't perform accurate coordinate calculation when coordinates
        in AltAz frame is involved. Please use :mod:`neclib.coordinates.convert` module
        for accurate coordinate calculation.

        """
        import numpy as np
        from astropy.time import Time

        from ...core import config
        from ..convert import CoordCalculator

        if not hasattr(self, "_calc"):
            self._calc = CoordCalculator(config.location)
        now = Time(time.time(), format="unix")

        nowhere = (float("nan") * u.deg, float("nan") * u.deg, "fk5")

        if self.name_query:
            coord = self._calc.name_coordinate(self.target or self.reference, now)
            coord = coord.realize()
        else:
            target = self.target or self.reference or nowhere
            coord = self._calc.coordinate(
                lon=target[0], lat=target[1], frame=target[2], time=now
            )

        if self.with_offset:
            delta = self._calc.coordinate_delta(
                d_lon=self.offset[0], d_lat=self.offset[1], frame=self.offset[2]
            )
            coord = coord.cartesian_offset_by(delta)

        if self.is_scan:
            delta_start = self._calc.coordinate_delta(
                self.start[0], self.start[1], self.scan_frame
            )
            delta_stop = self._calc.coordinate_delta(
                self.stop[0], self.stop[1], self.scan_frame
            )
            start = coord.cartesian_offset_by(delta_start)
            stop = coord.cartesian_offset_by(delta_stop)
            lon = np.r_[start.lon, stop.lon]
            lat = np.r_[start.lat, stop.lat]
            coord = self._calc.coordinate(
                lon=lon, lat=lat, frame=self.scan_frame, time=now
            )

        if coord.time is None:
            coord.time = time.time()

        return coord.skycoord


class ObservationSpec(Parameters, ABC):
    __slots__ = ("_executing",)
    _repr_frame: CoordFrameType = "fk5"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._executing: Optional[Generator[Waypoint, None, None]] = None

    @abstractmethod
    def observe(self) -> Generator[Waypoint, None, None]:
        """Define all the observation steps which will be interpreted and commanded."""
        ...

    def __next__(self) -> Waypoint:
        if self._executing is None:
            self._executing = self.observe()

        # If generator created above contain nothing, raise StopIteration
        if self._executing is None:
            raise StopIteration
        return next(self._executing)

    def __iter__(self) -> Iterator[Waypoint]:
        return self

    def _repr_html_(self) -> str:
        return super()._repr_html_() + html_repr_of_observation_spec(
            self, frame=self._repr_frame
        )

    def hot(self, id: Any = None, integration: Optional[u.Quantity] = None):
        # Infer the duration by general keyword
        if integration is None:
            integration = self["integ_hot"]
        return Waypoint(mode=ObservationMode.HOT, id=id, integration=integration)

    def off(
        self,
        id: Any = None,
        integration: Optional[u.Quantity] = None,
        *,
        relative: Optional[bool] = None,
        on_coord: Optional[CoordinateType] = None,
        off_coord: Optional[CoordinateType] = None,
    ) -> Waypoint:
        # Infer the duration by general keyword
        if integration is None:
            integration = self["integ_off"]
        if relative is None:
            relative = self["relative"]
        if on_coord is None:
            on_coord = self._reference
        if off_coord is None:
            if relative:
                lon, lat = self["delta_lambda"], self["delta_beta"]
                off_coord = (lon, lat, self["coord_sys"])
            else:
                off_coord = (self["lambda_off"], self["beta_off"], self["coord_sys"])

        kwargs = dict(mode=ObservationMode.OFF, id=id, integration=integration)
        if relative:
            kwargs.update(reference=on_coord, offset=off_coord)
        else:
            kwargs.update(target=off_coord)
        return Waypoint(**kwargs)

    @property
    def coords(self) -> pd.DataFrame:
        """Crudely calculated waypoints this object represents.

        Warning
        -------
        This property doesn't perform accurate coordinate calculation when coordinates
        in AltAz frame is involved.

        """
        waypoints = self.observe()
        waypoint_summary = []

        last_coord = None
        for i, wp in enumerate(waypoints):
            coord = wp.coordinates.transform_to(self._repr_frame)
            lon = coord.data.lon << u.deg
            lat = coord.data.lat << u.deg
            try:
                nan_coord = (lon != lon) or (lat != lat)
            except ValueError:
                nan_coord = (lon != lon).any() or (lat != lat).any()

            transition_lon, transition_lat = [], []
            if (coord.size == 0) or nan_coord:
                pass  # Cannot determine where the observation will be taken place.
            elif coord.size == 1:
                if last_coord is not None:
                    transition_lon = [last_coord[0], lon]
                    transition_lat = [last_coord[1], lat]
                last_coord = (lon, lat)
            else:
                if last_coord is not None:
                    transition_lon = [last_coord[0], lon[0]]
                    transition_lat = [last_coord[1], lat[0]]
                last_coord = (lon[-1], lat[-1])

            coord = [
                dict(lon=_lon, lat=_lat, mode=ObservationMode.DRIVE)
                for _lon, _lat in zip(transition_lon, transition_lat)
            ]
            try:
                _coord = [
                    dict(lon=_lon, lat=_lat, mode=wp.mode)
                    for _lon, _lat in zip(lon, lat)
                ]
                coord.extend(_coord)
            except TypeError:
                coord.extend([dict(lon=lon, lat=lat, mode=wp.mode)])

            for c in coord:
                drive = c["mode"] == ObservationMode.DRIVE
                c.update(
                    waypoint_index=i,
                    scan_frame=None if drive else wp.scan_frame,
                    speed=None if drive else wp.speed,
                    integration=None if drive else wp.integration,
                    id=None if drive else wp.id,
                )
            waypoint_summary.extend(coord)
        return pd.DataFrame(waypoint_summary).set_index("waypoint_index")

    @property
    def fig(self) -> plt.Figure:
        """Figure of crudely calculated telescope driving path.

        Notes
        -----
        If you need ``Axes`` object, use ``fig.axes`` attribute.

        """
        waypoints = self.coords

        with plt.style.context("dark_background"), plt.rc_context(
            {"font.family": "serif", "font.size": 9}
        ):
            fig, ax = plt.subplots(figsize=(3, 3), dpi=150)
            ax.set(
                xlabel="Longitude [deg]",
                ylabel="Latitude [deg]",
                title=f"Waypoints in {self._repr_frame.upper()} frame",
                aspect=1,
            )
            if self._repr_frame.lower() not in ["altaz", "horizontal", "azel"]:
                # Celestial coordinate frames are generally right-handed.
                ax.invert_xaxis()
            for _, _coords in waypoints.groupby(level=0):
                for mode, coords in _coords.groupby("mode", sort=False):
                    lon = coords["lon"] << u.deg
                    lat = coords["lat"] << u.deg
                    try:
                        nan_coord = (lon != lon) or (lat != lat)
                    except ValueError:
                        nan_coord = (lon != lon).any() or (lat != lat).any()

                    if nan_coord:
                        pass  # Cannot determine where to plot.
                    elif len(coords) == 1:
                        ax.plot(lon, lat, ".", c=mode.value, ms=5, alpha=0.9)
                    else:
                        ax.plot(
                            lon,
                            lat,
                            c=mode.value,
                            lw=0.5,
                            ms=1,
                            alpha=0.9,
                            zorder=-1 if mode == ObservationMode.DRIVE else 1,
                        )

            ax.grid(True, c="#767")
            fig.tight_layout()
            plt.close(fig)
            return fig

    @property
    def _reference(self) -> Union[str, Tuple[float, float, str]]:
        if None in (self["lambda_on"], self["beta_on"]):
            return self["target"]
        else:
            return (self["lambda_on"], self["beta_on"], self["coord_sys"])
