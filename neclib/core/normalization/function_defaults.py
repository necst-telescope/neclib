import functools
from inspect import Parameter, Signature, signature
from types import FunctionType, MethodType
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

from ..exceptions import NotInitializedError


class partial:
    def __init__(
        self,
        func: Any = None,
        /,
        *,
        args: Tuple[Any, ...] = (),
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        if isinstance(func, partial):
            func = func.func

        if (func is not None) and (not isinstance(func, (MethodType, FunctionType))):
            raise TypeError(
                f"Only function-like type supported, given {func} ({type(func)})"
            )
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def __call__(
        self, *args: Any, **kwargs: Any
    ) -> Union[Callable[..., Any], "partial"]:
        if (self.func is None) and (len(args) > 0):
            self.__init__(args[0], args=self.args, kwargs=self.kwargs)
            return self
        else:
            return self.create_wrapper(shift=0)(*args, **kwargs)

    def __get__(
        self, obj: object, objtype: Optional[Type[object]] = None
    ) -> Callable[..., Any]:
        return self.create_wrapper(shift=0 if obj is None else 1)

    def empty_parameters(
        self, args: Tuple[Any, ...], kwargs: Dict[str, Any], shift: int = 0
    ) -> List[str]:
        sig = self.signature
        empty_args = [
            list(sig.parameters.items())[i][0]
            for i, v in enumerate(args)
            if v == Parameter.empty
        ]
        empty_kwargs = [k for k, v in kwargs.items() if v == Parameter.empty]
        empty = empty_args + empty_kwargs
        return empty[min(len(empty), shift) :]

    def create_wrapper(self, shift: int = 0) -> Callable[..., Any]:
        @functools.wraps(self.func)
        def wrapper(*_args, **_kwargs):
            args_1 = self.parse_arguments(self.args, self.kwargs, True, shift)
            args_2 = self.parse_arguments(_args, _kwargs, False, shift)
            args, kwargs = self.merge_arguments(args_1, args_2)
            empty = self.empty_parameters(args, kwargs, shift=shift)
            if len(empty) > 0:
                raise TypeError(f"Values for argument {empty} not provided")
            return self.func(*args, **kwargs)

        return wrapper

    @property
    def signature(self) -> Signature:
        if self.func is None:
            raise NotInitializedError("Not attached to function-like object.")
        return signature(self.func)

    def parse_arguments(
        self,
        args: Tuple[Any, ...] = (),
        kwargs: Optional[Dict[str, Any]] = None,
        fallback: bool = False,
        shift: int = 0,
    ) -> Dict[Union[str, int], Any]:
        kwargs = kwargs or {}
        arguments = {}
        for i, param in enumerate(self.signature.parameters.values()):
            if param.kind == Parameter.POSITIONAL_ONLY:
                arguments[i] = param.default if fallback else Parameter.empty
            else:
                arguments[param.name] = param.default if fallback else Parameter.empty

        not_kw_only = filter(
            lambda x: x.kind != Parameter.KEYWORD_ONLY,
            self.signature.parameters.values(),
        )
        possibly_positional_count = len(list(not_kw_only))

        keys = tuple(arguments.keys())
        for i, arg in enumerate(args):
            if i < possibly_positional_count:
                k = keys[i + shift]
                arguments[k] = arg
        for k, kwarg in kwargs.items():
            if k in arguments:
                arguments[k] = kwarg

        return arguments

    def merge_arguments(
        self, *args: Dict[Union[str, int], Any]
    ) -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        """Merge arguments candidates.

        Parameters
        ----------
        args
            The (args, kwargs) pairs to be merged. The pair appears later takes
            precedence, so the default value would be given as first argument.

        """
        arguments = self.parse_arguments(fallback=True)
        for _args in args:
            not_empty = dict(
                filter(lambda item: item[1] != Parameter.empty, _args.items())
            )
            arguments.update(not_empty)
        return tuple(v for k, v in arguments.items() if isinstance(k, int)), {
            k: v for k, v in arguments.items() if isinstance(k, str)
        }
