# neclib.devices

NECST abstracts the devices; you can control devices without knowing the actual model.
To realize this feature, neclib defines common functions in base classes, and selects
the device models specified in the config file.

## How to specify the devices

Parameters prefixed with `dev_` in [config file](./config) are parsed as device
specifications. The key is parsed as [device name](#device-name), and the value the
[model](#device-model). The actual implementation is linked by
[neclib/devices/selector.py](https://github.com/necst-telescope/neclib/blob/main/neclib/devices/selector.py).

### Device name

The variable name the abstract device is referenced as.

````{attention}
The name would be defined in snake-case in config file, but will be converted to
camel-case to indicate the implementation is class object, like below.

```toml
dev_antenna_motor = "CPZ7415V"
```

The above configuration creates device name `AntennaMotor` linked to class `CPZ7415V`.

```python
>>> from neclib.devices import AntennaMotor
>>> AntennaMotor
neclib.devices.motor.cpz7415v.CPZ7415V
```

````

````{note}
The name isn't the same as device base class's. The latter just reveals its type, like
`Motor`, but the *device name* should be a little bit more concrete to uniquely specify
which device to handle, like `AntennaMotor`.

This also means you can use same model twice, as `AntennaMotor` and `M2Motor`, by
writing config file like below:

```toml
dev_antenna_motor = "CPZ7415V"
dev_m2_motor = "CPZ7415V"
```

````

### Device model

The unique key to distinguish the device model. Each device I/O class also defines its
identifier as class variable `Model`, which is used (case-insensitively) to search the
corresponding implementation.

## How to add device I/O class

### Definition of abstract device

```{note}
This procedure is only needed on adding new type of devices. When adding new model of
already defined device (found as subdirectories of
[neclib/devices](https://github.com/necst-telescope/neclib/tree/main/neclib/devices)),
skip this section.
```

The abstract device should be implemented as follows:

- Inherit from `ABC` to provide consistent API throughout the models
- Methods should be decorated by `abstractmethod` or `final`
  - `abstractmethod` is for methods requires model-specific implementation
  - `final` is for methods that can model-independently used
- Method names should use `set`/`get` prefix convention
- The definition file should be suffixed with `_base.py`

```python
from abc import ABC, abstractmethod
from typing import final

class DeviceType(ABC):
    Model: str
    Manufacturer: str = ""
    @abstractmethod
    def set_some_parameter(self, value: float) -> None:
        ...
    @abstractmethod
    def get_some_parameter(self) -> float:
        ...
    @final
    def get_all_data(self) -> dict[str, float]:
        return {"some_parameter": self.get_some_parameter()}
```

### Device-specific implementation

The device I/O class should be implemented as follows:

- Inherit from abstract class defined in `*_base.py`
- Define `Model` and `Manufacturer` class variables
  - Model name preferably omit non alphanumeric character, to avoid inconsistent
    reference
  - No strict limitation is imposed on class name, but is preferably the same as `Model`
- Define required methods (decorated with `@abstractmethod`)
  - You can freely add methods to implement the required ones
  - Don't define ones decorated with `@final`

```{note}
The device model are used case-insensitively in
[neclib/devices/selector.py](https://github.com/necst-telescope/neclib/blob/main/neclib/devices/selector.py),
so you cannot avoid duplicate by just using different case.
```

```python
from typing import Final
from .device_type_base import DeviceType

class DeviceModel(DeviceType):
    Model: Final[str] = "DeviceModel"
    Manufacturer: Final[str] = "Manufacturer"
    def set_some_parameter(self, value: float) -> None:
        # Implementation comes here
    def get_some_parameter(self) -> float:
        # Implementation comes here
        return self._some_method_to_implement_get_some_parameter()
    def _some_method_to_implement_get_some_parameter(self):
        # Implementation comes here
    # Don't define methods decorated with @final
```
