__all__ = ["describe_frame", "parse_frame"]

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Type, Union

from astropy.coordinates import (
    Angle,
    BaseCoordinateFrame,
    SkyOffsetFrame,
    frame_transform_graph,
)


@dataclass
class Frame:

    frame: Union[str, BaseCoordinateFrame, Type[BaseCoordinateFrame]]

    def __post_init__(self):
        if isinstance(self.frame, str):
            self.frame = self._parse(self.frame)

    def _parse(
        self, frame: str
    ) -> Union[BaseCoordinateFrame, Type[BaseCoordinateFrame]]:
        _parsed = frame_transform_graph.lookup_name(frame.lower())
        if _parsed is not None:
            return _parsed

        _parsed = re.match(
            r"origin\s*=\s*([a-z0-9]*)\(([a-z\d\s.]*),\s*([a-z\d\s.]*)\),\s*"
            r"rotation\s*=\s*([a-z\d\s.]*)",
            frame.lower(),
        )
        if _parsed is not None:
            base_frame, lon, lat, rotation = _parsed.groups()
            BaseFrame = frame_transform_graph.lookup_name(base_frame.lower())
            rotation = Angle(rotation)
            if BaseFrame is None:
                raise ValueError(f"Unknown frame {base_frame!r}")
            return SkyOffsetFrame(origin=BaseFrame(lon, lat), rotation=rotation)
        raise ValueError(f"Could not parse frame {frame!r}")

    def _describe(
        self, frame: Union[BaseCoordinateFrame, Type[BaseCoordinateFrame]]
    ) -> str:
        if "offset" not in frame.name:
            return frame.name
        center = frame.origin
        attr_names = center.representation_component_names
        attr_name_mapping = {v: k for k, v in attr_names.items()}
        lon = getattr(center, attr_name_mapping["lon"])
        lat = getattr(center, attr_name_mapping["lat"])
        return f"origin={center.name}({lon}, {lat}), rotation={frame.rotation}"

    @classmethod
    @lru_cache(maxsize=16)
    def from_string(cls, frame: str) -> "Frame":
        return cls(frame)

    def __str__(self) -> str:
        if "offset" not in self.frame.name:
            return self.frame.name
        return self._describe(self.frame)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._describe(self.frame)})"


def parse_frame(frame: str) -> Union[SkyOffsetFrame, Type[BaseCoordinateFrame]]:
    """Parse a frame string into a frame object.

    Parameters
    ----------
    frame
        The frame string to parse.

    Returns
    -------
    frame
        The frame object.

    Examples
    --------
    >>> neclib.coordinates.parse_frame("fk5")
    <class 'astropy.coordinates.builtin_frames.fk5.FK5'>
    >>> neclib.coordinates.parse_frame("altaz")
    <class 'astropy.coordinates.builtin_frames.altaz.AltAz'>
    >>> neclib.coordinates.parse_frame("origin=FK5(10deg, 0deg), rotation=20deg")
    <SkyOffsetFK5 Frame (equinox=J2000.000, rotation=20.0 deg, origin=<FK5 Coordinate
    (equinox=J2000.000): (ra, dec) in deg
    (10., 0.)>)>

    """
    return Frame.from_string(frame).frame


def describe_frame(frame: Union[BaseCoordinateFrame, Type[BaseCoordinateFrame]]) -> str:
    """String representation of a frame.

    Parameters
    ----------
    frame
        The frame to describe.

    Returns
    -------
    repr
        String representation of the frame.

    Examples
    --------
    >>> neclib.coordinates.describe_frame(FK5)
    'fk5'
    >>> neclib.coordinates.describe_frame(AltAz())
    'altaz'
    >>> neclib.coordinates.describe_frame(
    ...     SkyOffsetFrame(origin=FK5("10deg", "0deg"), rotation="20deg")
    ... )
    'origin=fk5(10deg, 0deg), rotation=20deg'

    """
    return str(Frame(frame))
