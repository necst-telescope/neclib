from typing import Optional, Type, TypeVar

from neclib.devices.device_base import DeviceBase

T = TypeVar("T", bound=DeviceBase)


def get_instance(type: Type[T]) -> Optional[T]:
    model_match = filter(lambda x: x.Model == type.Model, type._instances.values())
    manufacturer_match = filter(
        lambda x: x.Manufacturer == type.Manufacturer, model_match
    )
    return next(manufacturer_match, None)
