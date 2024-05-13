import warnings

import pytest

from neclib import (
    NECSTAccessibilityWarning,
    NECSTAuthorityError,
    NECSTConfigurationError,
    NECSTParameterNameError,
    NECSTTimeoutError,
)


class TestNECSTAuthorityError:
    def test_with_args(self):
        with pytest.raises(NECSTAuthorityError):
            raise NECSTAuthorityError("No privilege granted.")

    def test_without_args(self):
        with pytest.raises(NECSTAuthorityError):
            raise NECSTAuthorityError


class TestNECSTConfigurationError:
    def test_with_args(self):
        with pytest.raises(NECSTConfigurationError):
            raise NECSTConfigurationError("No configuration found.")

    def test_without_args(self):
        with pytest.raises(NECSTConfigurationError):
            raise NECSTConfigurationError


class TestNECSTTimeoutError:
    def test_with_args(self):
        with pytest.raises(NECSTTimeoutError):
            raise NECSTTimeoutError("Communication cannot be established.")

    def test_without_args(self):
        with pytest.raises(NECSTTimeoutError):
            raise NECSTTimeoutError


class TestNECSTAccessibilityWarning:
    def test_with_args(self):
        with pytest.raises(NECSTAccessibilityWarning):
            raise NECSTAccessibilityWarning("Limited usage.")

    def test_without_args(self):
        with pytest.raises(NECSTAccessibilityWarning):
            raise NECSTAccessibilityWarning

    def test_warning_support(self):
        with pytest.warns(NECSTAccessibilityWarning):
            warnings.warn("msg", category=NECSTAccessibilityWarning)


class TestNECSTParameterNameError:
    def test_with_args(self):
        with pytest.raises(NECSTParameterNameError):
            raise NECSTParameterNameError("Invalid parameter name.")

    def test_without_args(self):
        with pytest.raises(NECSTParameterNameError):
            raise NECSTParameterNameError
