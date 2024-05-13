from typing import Protocol


class ConfiguredTester(Protocol):
    @classmethod
    def setup_class(cls) -> None: ...

    @classmethod
    def teardown_class(cls) -> None: ...
