import pytest
from neclib import NECSTAuthorityError


class TestNECSTAuthorityError:
    def test_exception_type(self):
        with pytest.raises(NECSTAuthorityError):
            raise NECSTAuthorityError("No authority.")
