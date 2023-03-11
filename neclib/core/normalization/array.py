from typing import Any, Generic, TypeVar

import numpy as np
import numpy.typing as npt

T = TypeVar("T")


class NPArrayValidator(Generic[T]):
    """Type validator, to force some instance variables to be Quantity."""

    # For details on validator descriptor design, see:
    # https://docs.python.org/3/howto/descriptor.html#validator-class

    def __set_name__(self, owner: Any, name: str) -> None:
        self.private_name = "_" + name

    def __get__(self, instance: Any, owner: Any) -> npt.NDArray[T]:  # type: ignore
        if instance is None:
            raise AttributeError(f"Cannot access attribute {self.private_name!r}")
        return getattr(instance, self.private_name)

    def __set__(self, instance: Any, value: npt.ArrayLike) -> None:
        if not isinstance(value, np.ndarray):
            value = np.asanyarray(value)
        setattr(instance, self.private_name, value)
