import pytest

from neclib.core.security import sanitize


class TestSanitize:
    def test_pass_constant(self) -> None:
        sanitize("1")
        sanitize("1.0")
        sanitize("1.0e-3")
        sanitize("1.0e+3")
        sanitize("-1.0")
        sanitize("True")
        sanitize("False")
        sanitize("None")

    def test_pass_variable_identical(self) -> None:
        sanitize("x", known_variables="x")
        sanitize("x_ray", known_variables=["x_ray"])
        sanitize("y", known_variables=["x", "y"])

    def test_pass_variable_scaled(self) -> None:
        sanitize("x * 2", known_variables="x") == "x * 2"
        sanitize("2 * xray", known_variables=["xray"]) == "2 * xray"
        sanitize("yankee * 2", known_variables=["x", "yankee"]) == "yankee * 2"

    def test_pass_variable_shifted(self) -> None:
        sanitize("x + 2", known_variables="x") == "x + 2"
        sanitize("2 + x", known_variables=["x"]) == "2 + x"
        sanitize("y + 2", known_variables=["x", "y"]) == "y + 2"

    def test_pass_multiple_variables(self) -> None:
        sanitize("x + y", known_variables=["x", "y"])
        sanitize("x + y + z", known_variables=["x", "y", "z"])

    def test_fail_unknown_variable(self) -> None:
        with pytest.raises(ValueError):
            sanitize("x")

        with pytest.raises(ValueError):
            sanitize("x", known_variables=["y"])

        with pytest.raises(ValueError):
            sanitize("5 * x", known_variables=["xray"])

        with pytest.raises(ValueError):
            sanitize("5.1 + x", known_variables=["x_ray"])

    def test_fail_known_and_unknown_variable_mixed(self) -> None:
        with pytest.raises(ValueError):
            sanitize("x + y", known_variables=["x"])

        with pytest.raises(ValueError):
            sanitize("x + y + z", known_variables=["x", "y", "zulu"])

    def test_disallow_too_long_expression(self) -> None:
        with pytest.raises(ValueError):
            sanitize("x * " * 25 + "x")  # len=101

        with pytest.raises(ValueError):
            sanitize("x * " * 25 + "x", known_variables=["x"])

        with pytest.raises(ValueError):
            sanitize("x" * 101, known_variables=["x"])

        with pytest.raises(ValueError):
            sanitize("x" * 101, known_variables=["x", "y"])

        with pytest.raises(ValueError):
            sanitize("x + y", known_variables=["x", "y", "z"], max_length=1)
