from abc import abstractmethod

from ..device_base import DeviceBase


class Membrane(DeviceBase):

    Manufacturer: str = ""
    Model: str

    @abstractmethod
    def memb_open(self) -> None:
        """Open membrane."""
        ...

    @abstractmethod
    def memb_close(self) -> None:
        """Close membrane."""
        ...

    @abstractmethod
    def get_memb_status(self):
        # Type hints are not written because the way to write them
        # differs depending on the version.
        """Get status of membrane."""
        ...
