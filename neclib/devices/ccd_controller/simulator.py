from .ccd_controller_base import CCDController


class CCDControllerSimulator(CCDController):
    Manufacturer: str = ""
    Model: str = ""
    Identifier = ""
    is_simulator = True

    def __init__(self) -> None:
        pass

    def capture(self, savepath: str) -> None:
        pass

    def finalize(self) -> None:
        pass
