import pytest

from neclib.core import environ

variable = pytest.mark.parametrize("variable", environ.__all__)


class TestEnviron:
    @variable
    def test_environ(self, variable: str) -> None:
        assert hasattr(environ, variable)

    @variable
    def test_name(self, variable: str) -> None:
        assert getattr(environ, variable).name.isupper()

    @variable
    def test_value_type(self, variable: str) -> None:
        assert isinstance(getattr(environ, variable).get(), (str, type(None)))
