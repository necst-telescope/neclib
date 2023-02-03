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
from ...core.type_aliases import CoordFrameType, CoordinateType, UnitType
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
        return bool((self.count - self.last) > self.interval)

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
            self.count += unity

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
        from ..frame import parse_frame

        if not hasattr(self, "_calc"):
            self._calc = CoordCalculator(config.location)
        now = Time(time.time(), format="unix")

        nowhere = (float("nan") * u.deg, float("nan") * u.deg, "fk5")

        if self.name_query:
            coord = self._calc.get_body(self.target or self.reference, now)
        else:
            target = self.target or self.reference or nowhere
            coord = self._calc.get_skycoord(*target[:2], frame=target[2], obstime=now)

        if self.with_offset:
            offset_frame = self.offset[2]
            if isinstance(offset_frame, str):
                offset_frame = parse_frame(offset_frame)
            converted = coord.transform_to(offset_frame)
            lon = converted.data.lon + self.offset[0]
            lat = converted.data.lat + self.offset[1]
            coord = self._calc.get_skycoord(lon, lat, frame=self.offset[2], obstime=now)

        if self.is_scan:
            now_broadcasted = np.broadcast_to(now, (2,))
            scan_frame = self.scan_frame
            if isinstance(scan_frame, str):
                scan_frame = parse_frame(scan_frame)
            converted = coord.transform_to(scan_frame)
            ref_lon, ref_lat = converted.data.lon, converted.data.lat
            lon = np.r_[ref_lon + self.start[0], ref_lon + self.stop[0]]
            lat = np.r_[ref_lat + self.start[1], ref_lat + self.stop[1]]
            coord = self._calc.get_skycoord(
                lon, lat, frame=self.scan_frame, obstime=now_broadcasted
            )

        return coord


class ObservationSpec(Parameters, ABC):
    __slots__ = ("_executing", "_coords", "_fig")
    _repr_frame: CoordFrameType = "fk5"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._executing: Optional[Generator[Waypoint, None, None]] = None
        self._coords: Optional[Waypoint] = None
        self._fig: Optional[plt.Figure] = None

    @property
    def coords(self) -> pd.DataFrame:
        """Crudely calculated waypoints this object represents.

        Warning
        -------
        This property doesn't perform accurate coordinate calculation when coordinates
        in AltAz frame is involved.

        """
        if self._coords is None:
            self._coords = ...
            raise NotImplementedError
        return self._coords

    @property
    def fig(self) -> plt.Figure:
        """Figure of crudely calculated telescope driving path.

        Notes
        -----
        If you need ``Axes`` object, use ``fig.axes`` attribute.

        """
        if self._fig is None:
            self._fig = ...
            raise NotImplementedError
        return self._fig

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
        # TODO: Use properties ``coords`` and ``fig`` to show the path
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
        off_coord: Optional[CoordinateType] = None
    ) -> Waypoint:
        # Infer the duration by general keyword
        if integration is None:
            integration = self["integ_off"]
        if relative is None:
            relative = self["relative"]
        if on_coord is None:
            on_coord = (self["lambda_on"], self["beta_on"], self["coord_sys"])
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
