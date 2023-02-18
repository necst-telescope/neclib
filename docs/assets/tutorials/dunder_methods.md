# Dunder objects (any object with name `__***__`)

Dunder (Double UNDERscore) objects have special meaning in Python. They define Python's
automated behavior such as item access and class initialization.

```{important}
__You must pay attention when using dunder names__, since they define Python's language
spec. Invalid modification on them can break your whole software.

On the other hand, __you should modify them__ in sake of convenient and simple application development.
```

## Methods　to be defined by user

### `__init__`

Should return nothing (`None`).

### `__init_subclass__`

Automatically `classmethod` without decorator, should return nothing (`None`).

### `__new__`

Automatically `classmethod` without decorator, should return class instance. Returning
something which is not an instance of the class or its subclass won't raise any error,
but the behavior differs. See below for the details.

````{admonition} Example

1. `A.__new__` returns an instance of `A`
   ```python
   class A:
       def __new__(cls, *args, **kwargs):
           return super().__new__(cls)
       def __init__(self, *args, **kwargs):
           print("a")
   ```
   In this case, the following 2 snippets are almost equivalent:
   ```python
   >>> A(1, 2, 3, a=4, b=5)
   a
   ```
   ```python
   >>> instance_of_A = A.__new__(A, 1, 2, 3, a=4, b=5)
   >>> instance_of_A.__init__(1, 2, 3, a=4, b=5)
   a
   ```

2. `A.__new__` returns an instance of `B`, which is subclass of `A`
   ```python
   class A:
       def __new__(cls, a, b):
           return super().__new__(B)
       def __init__(self, a, b):
           print(self.__class__.__name__)
   class B(A):
       ...
   ```
   In this case, the behavior is almost the same as case 1, just minor swap of classes involved.
   ```python
   >>> A(1, 2, 3, a=4, b=5)
   B
   ```
   ```python
   >>> instance_of_B = A.__new__(A, 1, 2, 3, a=4, b=5)
   >>> instance_of_B.__init__(1, 2, 3, a=4, b=5)
   B
   ```
   When class `B` is called, the behavior is exactly equivalent to case 1.
   ```python
   >>> B(1, 2, 3, a=4, b=5)
   B
   ```
   ```python
   >>> instance_of_B = B.__new__(B, 1, 2, 3, a=4, b=5)
   >>> instance_of_B.__init__(1, 2, 3, a=4, b=5)
   B
   ```

3. `A.__new__` returns an instance of `C`, which is irrelevant to `A`
   ```python
   class A:
       def __new__(cls, a, b):
           return super().__new__(C)
       def __init__(self, a, b):
           print(self.__class__.__name__)
   class C:
       ...
   ```

````

### `__set__`, `__get__`, `__set_name__`, `__del__`

### `__getattr__`

### `__getitem__`

## Built-in methods

### `__subclasses__`

## Variables

### `__class__`

### `__name__`
