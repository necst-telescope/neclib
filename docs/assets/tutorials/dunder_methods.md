# Dunder objects (any object with name `__***__`)

Dunder (Double UNDERscore) objects have special meaning in Python. They define Python's
automated behavior such as item access and class initialization.

```{important}
__You must pay attention when using dunder names__, since they define Python's language
spec. Invalid modification on them can break your whole software.

On the other hand, __you should modify them__ in sake of convenient and simple
application development.
```

## Methods to be defined by user

### `__init__`

Should return nothing (`None`). This method is called every time you call a class
object, even if the call returns exact same instance as before (singleton pattern).

This is a good place to define instance variables the class holds, since this method is
called every time a instance was created. In singleton class, you should pay attention
about this feature, as it can cause unexpected initialization of the class state.

````{admonition} Example

1. `A` is a class that accepts no argument on initialization

   ```python
   class A:
       def __init__(self):
           print("__init__ has been run")
   ```

   For simple class defined above, `__init__` is run every time you call `A`.

   ```python
   >>> A()
   __init__ has been run
   >>> A()
   __init__ has been run
   ```

2. `A` is a class that accepts arguments on initialization

   ```python
   class A:
       def __init__(self, a, b):
           print(f"__init__ has been run with arguments {a=}, {b=}")
   ```

   In this case arguments to the class `A` immediately passed to `__init__`.

   ```python
   >>> A(1, "q")
   __init__ has been run with arguments a=1, b=q
   >>> A("abc", 123)
   __init__ has been run with arguments a=abc, b=123
   ```

3. `A` is a singleton class

   ```python
   class A:
       _instance = None
       def __new__(cls, a, b):
           if cls._instance is None:
               cls._instance = super().__new__(cls)
           return cls._instance
       def __init__(self, a, b):
           print(f"__init__ has been run with arguments {a=}, {b=}")
   ```

   On the first call of `A`, the class creates new instance `instance1`. After that,
   call on `A` returns the exact same instance as the first one, so `instance2` is not a
   new instance but just another name for `instance1`.

   Even in this situation, the `__init__` method is called every time you call the class
   `A`, no matter if new instance was created or not.

   ```python
   >>> instance1 = A(1, "q")
   __init__ has been run with arguments a=1, b=q
   >>> instance2 = A("abc", 123)
   __init__ has been run with arguments a=abc, b=123
   >>> instance1 is instance2
   True
   ```

````

````{tip}

Setting a value to class variable from inside its instance is a little bit tricky. The
class variables can be accessed as `self`'s attribute (`self.<variable_name>`), but
setting a value in the same manner (`self.<variable_name> = new_value`) won't modify
the class variable, instead you may define new instance variable.

Since instance variables always take precedence on `self`'s attribute search, the above
situation effectively obscure the class variable.

```python
class A:
    classvar = 1
    def __init__(self, new_value):
        print(f"{self.classvar=}")
        self.classvar = new_value
        print(f"{self.classvar=}")
```

```python
>>> a = A(100)
self.classvar=1
self.classvar=100
>>> a.classvar
100  # Seems the class variable has been modified
>>> A.classvar
1  # But actually not
>>> a.__class__.__dict__
{'classvar': 1}  # This is the class variable
>>> a.__dict__
{'classvar': 100}  # This is the instance variable
```

````

### `__init_subclass__`

Automatically `classmethod` without decorator, should return nothing (`None`). This
method is called every time you create subclass of the class which this method is
defined on.

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
   In this case, the behavior is almost the same as case 1, just minor swap of classes
   involved.
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

### `__call__`

## Built-in methods

### `__subclasses__`

## Variables

### `__class__`

### `__name__`
