import pytest

from neclib.core import deprecated, deprecated_namespace


class TestDeprecated:
    def test_no_args_func(self) -> None:
        @deprecated
        def func(a=1):
            return a

        with pytest.warns(DeprecationWarning):
            assert func() == 1
        with pytest.warns(DeprecationWarning):
            assert func(9) == 9

    def test_no_args_method(self) -> None:
        class A:
            @deprecated
            def func(self, a=1):
                return a

        with pytest.warns(DeprecationWarning):
            assert A().func() == 1
        with pytest.warns(DeprecationWarning):
            assert A().func(9) == 9

    def test_no_args_class(self) -> None:
        @deprecated
        class A:
            def __init__(self, a=1):
                self.a = a

        with pytest.warns(DeprecationWarning):
            assert A().a == 1
        with pytest.warns(DeprecationWarning):
            assert A(9).a == 9

    def test_func(self) -> None:
        @deprecated(version_since="0.1.0", version_removed="0.2.0")
        def func(a=1):
            return a

        with pytest.warns(DeprecationWarning, match="version 0.1.0"):
            assert func() == 1
        with pytest.warns(DeprecationWarning, match="version 0.1.0"):
            assert func(a=9) == 9

    def test_method(self) -> None:
        class A:
            @deprecated(version_since="0.1.0", version_removed="0.2.0")
            def func(self, a=1):
                return a

        with pytest.warns(DeprecationWarning, match="version 0.1.0"):
            assert A().func() == 1
        with pytest.warns(DeprecationWarning, match="version 0.1.0"):
            assert A().func(9) == 9

    def test_class(self) -> None:
        @deprecated(version_since="0.1.0", version_removed="0.2.0")
        class A:
            def __init__(self, a=1):
                self.a = a

        with pytest.warns(DeprecationWarning, match="version 0.1.0"):
            assert A().a == 1
        with pytest.warns(DeprecationWarning, match="version 0.1.0"):
            assert A(9).a == 9


class TestDeprecatedNamespace:
    def test_no_args(self) -> None:
        from neclib import core

        depr_core = deprecated_namespace(core, "neclib.core")

        with pytest.warns(DeprecationWarning):
            assert depr_core.NECSTAuthorityError is core.NECSTAuthorityError

    def test_with_args(self) -> None:
        from neclib import core

        depr_core = deprecated_namespace(
            core,
            "neclib.core",
            version_since="0.1.0",
            version_removed="0.2.0",
        )

        with pytest.warns(DeprecationWarning, match="version 0.1.0"):
            assert depr_core.NECSTAuthorityError is core.NECSTAuthorityError
