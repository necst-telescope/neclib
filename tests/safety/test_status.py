import pytest

from neclib.safety import Status


class TestStatus:
    def test_assignment(self):
        status = Status()

        status["topic1"].warning = True
        assert status["topic1"].warning is True
        assert status["topic1"].critical is None  # None represents falsy but unknown

        status["topic2"] = {"warning": False, "critical": False}
        assert status["topic2"].warning is False
        assert status["topic2"].critical is False

        assert status.warning() is True
        assert status.critical() is False

    def test_custom_level(self):
        status = Status(["warning", "error", "critical"])

        status["topic1"].warning = True
        assert status["topic1"].warning is True
        assert status["topic1"].error is None  # None represents falsy but unknown
        assert status["topic1"].critical is None  # None represents falsy but unknown

        status["topic2"] = {"warning": False, "critical": False}
        assert status["topic2"].warning is False
        assert status["topic2"].error is None  # None represents falsy but unknown
        assert status["topic2"].critical is False

        assert status.warning() is True
        assert status.critical() is False

    def test_severity_propergation(self):
        status = Status()

        status["topic1"].critical = True
        assert status["topic1"].warning is None  # None represents falsy but unknown

        assert status.critical() is True
        assert status.warning() is True

    def test_reject_reserved_level(self):
        with pytest.raises(ValueError):
            Status(["warning", "critical", "__init__"])
