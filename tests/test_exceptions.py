import pytest

from neclib import NECSTAuthorityError, NECSTConfigurationError, NECSTTimeoutError


class TestNECSTAuthorityError:
    def test_exception_type(self):
        with pytest.raises(NECSTAuthorityError):
            raise NECSTAuthorityError("No privilege granted.")


class TestNECSTConfigurationError:
    def test_exception_type(self):
        with pytest.raises(NECSTConfigurationError):
            raise NECSTConfigurationError("No configuration found.")


class TestNECSTTimeoutError:
    def test_exception_type(self):
        with pytest.raises(NECSTTimeoutError):
            raise NECSTTimeoutError("Communication cannot be established.")
