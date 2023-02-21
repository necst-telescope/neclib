from typing import Tuple

import pytest

from neclib.core import partial


class TestPartial:
    def test_partial_function(self) -> None:
        def a(p: int, q: int) -> Tuple[int, int]:
            return p, q

        assert partial(a, kwargs=dict(q=1))(3) == (3, 1)
        assert partial(a, kwargs=dict(p=1))(3, 4) == (3, 4)
        assert partial(a, kwargs=dict(p=1))(q=3) == (1, 3)
        assert partial(a, args=(3, 4))() == (3, 4)
        assert partial(a, args=(3,), kwargs=dict(q=7))() == (3, 7)

    def test_partial_method(self) -> None:
        class A:
            def a(self, p: int, q: int) -> Tuple[int, int]:
                return p, q

        assert partial(A().a, kwargs=dict(q=1))(3) == (3, 1)
        assert partial(A().a, kwargs=dict(p=1))(3, 4) == (3, 4)
        assert partial(A().a, kwargs=dict(p=1))(q=3) == (1, 3)
        assert partial(A().a, args=(3, 4))() == (3, 4)
        assert partial(A().a, args=(3,), kwargs=dict(q=7))() == (3, 7)

    def test_positional_only(self) -> None:
        def a(p: int, /, q: int) -> Tuple[int, int]:
            return p, q

        assert partial(a, kwargs=dict(q=1))(3) == (3, 1)
        assert partial(a, kwargs=dict(p=1))(3, 4) == (3, 4)  # p=1 ignored
        with pytest.raises(TypeError):
            assert partial(a, kwargs=dict(p=1))(q=3) == (1, 3)
        assert partial(a, args=(3, 4))() == (3, 4)
        assert partial(a, args=(3,), kwargs=dict(q=7))() == (3, 7)

    def test_keyword_only(self) -> None:
        def a(p: int, *, q: int) -> Tuple[int, int]:
            return p, q

        assert partial(a, kwargs=dict(q=1))(3) == (3, 1)
        with pytest.raises(TypeError):
            assert partial(a, kwargs=dict(p=1))(3, 4) == (3, 4)
        assert partial(a, kwargs=dict(p=1))(q=3) == (1, 3)
        with pytest.raises(TypeError):
            assert partial(a, args=(3, 4))() == (3, 4)
        assert partial(a, args=(3,), kwargs=dict(q=7))() == (3, 7)

    def test_defaults_already_defined(self) -> None:
        def a(p: int, q: int = 99) -> Tuple[int, int]:
            return p, q

        assert partial(a, kwargs=dict(p=1))() == (1, 99)
        assert partial(a, kwargs=dict(p=1))(3) == (3, 99)
        assert partial(a, kwargs=dict(p=1))(3, 4) == (3, 4)
        assert partial(a, kwargs=dict(p=1))(q=3) == (1, 3)
        assert partial(a, args=(3, 4))() == (3, 4)
        assert partial(a, args=(3,), kwargs=dict(q=7))() == (3, 7)

    def test_missing_args_are_error(self) -> None:
        def a(p: int, q: int) -> Tuple[int, int]:
            return p, q

        with pytest.raises(TypeError):
            partial(a, kwargs=dict(p=1))()

    def test_missing_kwargs_are_error(self) -> None:
        def a(p: int, *, q: int) -> Tuple[int, int]:
            return p, q

        with pytest.raises(TypeError):
            partial(a, kwargs=dict(p=1))()

    def test_too_many_args_are_ignored(self) -> None:
        def a(p: int, q: int) -> Tuple[int, int]:
            return p, q

        assert partial(a, args=(1, 2, 3))() == (1, 2)
        assert partial(a, args=(1, 2, 3))(2, 4) == (2, 4)

    def test_nonexistent_kwargs_are_ignored(self) -> None:
        def a(p: int, q: int) -> Tuple[int, int]:
            return p, q

        assert partial(a, kwargs=dict(p=1, q=2, r=3))() == (1, 2)
        assert partial(a, kwargs=dict(p=1, q=2, r=3))(2, q=4) == (2, 4)

    def test_non_function_obj_is_error(self) -> None:
        with pytest.raises(TypeError):
            partial(..., kwargs=dict(p=1, q=2, r=3))()
        with pytest.raises(TypeError):
            partial(1, kwargs=dict(p=1, q=2, r=3))()

    def test_decorator_use(self) -> None:
        @partial(args=(5, 6))
        def a(p: int, q: int) -> Tuple[int, int]:
            return p, q

        assert a() == (5, 6)
        assert a(7) == (7, 6)

        class A:
            @partial(kwargs=dict(r=5), args=(3,))
            def a(self, p, q, r) -> Tuple[int, int, int]:
                return p, q, r

        assert A().a(q=0) == (3, 0, 5)
        assert A().a(2, 1) == (2, 1, 5)
