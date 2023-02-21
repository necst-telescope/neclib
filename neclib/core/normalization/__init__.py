"""Collection of type converters which allow type-flexible read-in."""

from .function_defaults import partial
from .quantity import get_quantity

__all__ = ["get_quantity", "partial"]
