"""Definition of environment variable names recognized by NECST."""

__all__ = [
    "necst_root",
    "ros2_ws",
    "domain_id",
    "record_root",
    "debug_mode",
    "log_level",
]

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class EnvironmentVariable:
    name: str
    """Name of the environment variable."""
    default: Optional[str] = None
    """Default value of the environment variable."""

    def get(self) -> Optional[str]:
        """Get the value of the environment variable."""
        return os.environ.get(self.name, self.default)


necst_root = EnvironmentVariable("NECST_ROOT")
ros2_ws = EnvironmentVariable("ROS2_WS")
domain_id = EnvironmentVariable("ROS_DOMAIN_ID")
record_root = EnvironmentVariable("NECST_RECORD_ROOT")
debug_mode = EnvironmentVariable("NECST_DEBUG_MODE")
log_level = EnvironmentVariable("NECST_LOG_LEVEL", "INFO")
