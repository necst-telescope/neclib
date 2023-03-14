__all__ = ["describe_frame", "parse_frame"]

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, ClassVar, Dict, Type, Union

from astropy.coordinates import (
    Angle,
    BaseCoordinateFrame,
    SkyOffsetFrame,
    frame_transform_graph,
)


@dataclass
class Frame:
    """Converts between frame objects and their string representations."""

    frame: Union[BaseCoordinateFrame, Type[BaseCoordinateFrame]]
    """Frame object."""

    aliases: ClassVar[Callable[[], Dict[str, str]]] = lambda: {
        "j2000": "fk5",
        "b1950": "fk4",
        "horizontal": "altaz",
    }
    """A dictionary of coordinate frame name dialects."""
    # Since dictionary is mutable, this alias list is defined as a callable.

    @staticmethod
    def _parse(frame: str) -> Union[BaseCoordinateFrame, Type[BaseCoordinateFrame]]:
        """Convert a string representation into a frame object."""
        # Search for the frame in AstroPy's built-in frames
        _parsed = frame_transform_graph.lookup_name(frame.lower())
        if _parsed is not None:
            return _parsed

        # Parse SkyOffsetFrame specs
        _parsed = re.match(
            r"origin=([a-z0-9]*)\(-?([a-z\d\.]*),-?([a-z\d\.]*)\),"
            r"rotation=(-?[a-z\d\.]*)",
            frame.lower().replace(" ", ""),
        )
        if _parsed is not None:
            base_frame, lon, lat, rotation = _parsed.groups()
            BaseFrame = frame_transform_graph.lookup_name(base_frame.lower())
            rotation = Angle(rotation)
            if BaseFrame is None:
                raise ValueError(f"Unknown frame {base_frame!r}")
            return SkyOffsetFrame(origin=BaseFrame(lon, lat), rotation=rotation)
        raise ValueError(f"Could not parse frame {frame!r}")

    @staticmethod
    def _describe(frame: Union[BaseCoordinateFrame, Type[BaseCoordinateFrame]]) -> str:
        """Convert a frame object into a string representation."""
        # Built-in frames
        if not isinstance(frame, SkyOffsetFrame):
            return frame.name  # type: ignore

        # Get string representation of SkyOffsetFrame
        center: BaseCoordinateFrame = frame.origin  # type: ignore
        attr_names = center.representation_component_names
        attr_name_mapping = {v: k for k, v in attr_names.items()}
        lon = getattr(center, attr_name_mapping["lon"])
        lat = getattr(center, attr_name_mapping["lat"])

        origin = f"{center.name}({lon}, {lat})"
        rotation = f"{frame.rotation}"
        return f"origin={origin}, rotation={rotation}"

    @classmethod
    @lru_cache(maxsize=16)
    def from_string(cls, frame: str, /) -> "Frame":
        """Create Frame object, parsing string representation."""
        frame = frame.lower()
        for k, v in cls.aliases().items():
            frame = frame.replace(k, v)
        parsed_frame = cls._parse(frame)
        return cls(parsed_frame)

    def __str__(self) -> str:
        return self._describe(self.frame)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._describe(self.frame)})"


def parse_frame(frame: str, /) -> Union[Type[BaseCoordinateFrame], BaseCoordinateFrame]:
    """Parse a frame string and create a frame object.

    Parameters
    ----------
    frame
        String representation of coordinate frame.

    Returns
    -------
    Parsed frame object.

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


def describe_frame(
    frame: Union[BaseCoordinateFrame, Type[BaseCoordinateFrame]], /
) -> str:
    """Get string representation of a frame.

    Parameters
    ----------
    frame
        Frame object to describe.

    Returns
    -------
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
