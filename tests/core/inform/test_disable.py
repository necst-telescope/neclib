import pytest

from neclib.core import disabled


class TestDisabled:
    def test_disabled_function(self) -> None:
        @disabled
        def func() -> None:
            pass

        with pytest.raises(NotImplementedError):
            func()

    def test_disabled_lambda_function(self) -> None:
        with pytest.raises(NotImplementedError):
            disabled(lambda: None)()

    def test_disabled_method(self) -> None:
        class A:
            @disabled
            def method(self) -> None:
                pass

        with pytest.raises(NotImplementedError):
            A().method()

    @pytest.mark.skip(reason="Not implemented yet")
    def test_disabled_class(self) -> None:
        @disabled
        class A:
            pass

        with pytest.raises(NotImplementedError):
            A()
