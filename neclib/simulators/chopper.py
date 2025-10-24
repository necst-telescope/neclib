"""Emulator for chopper motion and corresponding current position."""

__all__ = ["ChopperEmulator"]


class ChopperEmulator:

    def __init__(self,):
        self.position = "insert"

    def set_step(self, position, axis):
        self.position = position

    def get_step(self, axis):
        return self.position

