"""Emulator for chopper motion and corresponding current position."""

__all__ = ["AntennaEncoderEmulator"]

import time
from typing import Callable, ClassVar, List, Literal, Tuple, Union

import astropy.units as u
import numpy as np

from .. import utils
from ..core import math
from ..core.types import AngleUnit
from ..utils import AzElData, ParameterList



class AntennaEncoderEmulator:

    def __init__(self,):
        self.position="insert"

    def set_step(self, position, axis):
        self.position = position

    def get_step(self, axis):
        return self.position

