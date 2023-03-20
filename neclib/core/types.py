from typing import (
    Any,
    Callable,
    ClassVar,
    Generic,
    Literal,
    Protocol,
    Tuple,
    Type,
    TypeVar,
    Union,
    runtime_checkable,
)

import numpy as np
import numpy.typing as npt
from astropy.coordinates import BaseCoordinateFrame
from astropy.units import Quantity, UnitBase

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)


class Array(Protocol, Generic[T_co]):
    def __getitem__(self, index: Any, /) -> Union[T, "Array[T]"]:
        ...


DimensionLess = Union[int, float, npt.NDArray[np.number], Array[Union[int, float]]]
"""Type alias for values with no physical units."""

UnitType = Union[UnitBase, str]
"""Type alias for objects that represents physical unit."""

CoordFrameType = Union[str, BaseCoordinateFrame, Type[BaseCoordinateFrame]]
"""Type alias for objects that represents coordinate frame."""

EquivalencyType = Tuple[
    UnitBase, UnitBase, Callable[[float], float], Callable[[float], float]
]
"""Type alias for unit equivalency in ``astropy.units``."""

AngleUnit = Literal["deg", "rad", "arcmin", "arcsec"]
"""Type alias for supported angular units."""

CoordinateType = Tuple[Quantity, Quantity, CoordFrameType]
"""Type alias for coordinate in (lon, lat, frame) format."""


@runtime_checkable
class SupportsComparison(Protocol):
    def __eq__(self: T, other: T, /) -> bool:
        ...

    def __ne__(self: T, other: T, /) -> bool:
        ...

    def __lt__(self: T, other: T, /) -> bool:
        ...

    def __le__(self: T, other: T, /) -> bool:
        ...

    def __gt__(self: T, other: T, /) -> bool:
        ...


@runtime_checkable
class TextLike(Protocol):
    def upper(self) -> "TextLike":
        ...

    def lower(self) -> "TextLike":
        ...

    def find(self) -> int:
        ...

    def replace(self) -> "TextLike":
        ...

    def __len__(self) -> int:
        ...


@runtime_checkable
class IsDataClass(Protocol):
    __dataclass_fields__: ClassVar[dict]
