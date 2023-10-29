from abc import abstractmethod

from ..device_base import DeviceBase


class CCDController(DeviceBase):
    @abstractmethod
    def capture(self) -> None:
        ...

    @abstractmethod
    def finalize(self) -> None:
        ...
