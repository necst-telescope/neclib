# neclib.config

NECST is designed to be general, observatory-nonspecific software. The parameters
specific to perticular observatory are defined in single parameter file. These are the
key implementations for the extensibility of NECST.

## The config file

### Location of the file

The file is automatically searched on import of neclib, in the following order.

1. If a environment variable `NECST_ROOT` is set:
   1. If it points to a file, that file will be read
   2. If it points to a directory, `$NECST_ROOT/config.toml` will be read if exists
2. If the environment variable isn't set or the file `$NECST_ROOT/config.toml` wasn't
   found:
   1. Default configuration file included in this package
      [neclib/src/config.toml](https://github.com/necst-telescope/neclib/blob/main/neclib/src/config.toml)
      will be read

```{important}
Error on parsing the file won't be caught, so when the existing file is specified via
environment variable, default config file won't be imported.
```

````{tip}
If you want to read non-default config file (e.g. importing config file saved in
observation record), overwrite the environment variable and reload the configuration,
like below.

```python
>>> from neclib import config
>>> import os
>>> os.environ["NECST_ROOT"] = "path/to/record/config.toml"
>>> config.reload()
```

````

### How to define parameters

The config file is written in [TOML](https://toml.io/) syntax, and is parsed by
[tomlkit](https://pypi.org/project/tomlkit/). The following is the list of restrictions
and preferences on the contents.

- First of all, the file should be written in valid TOML syntax
- Parameters will be defined as key-value pair
  - Any valid TOML type will be accepted as the value: Array, Inline-table, Array of
    tables, Integer, Float, Boolean, Datetime, and String
  - Use of Table (not inline version) is strongly discouraged (won't cause parse error,
    but can cause unexpected parsing result)
- Parameter name (key) should use snake-case (words are split by underscores)
- Lower case is preferred for the parameter names, for simplicity
- Parameter names should be prefixed to indicate the relative parameters
  - See [How to Use the Parameters](#how-to-use-the-parameters)  section for the details
- Use of comments are encouraged, but don't be satisfied of it. Please document the spec
  in [Parameter Reference](https://necst-telescope.github.io/neclib/docs/parameters/index.html)
  (for general parameters) or
  [device controller documents](https://necst-telescope.github.io/neclib/_source/neclib.devices.html)
  (for device-specific parameters).

The following parameter definitions are valid and preferred:

```toml
antenna_max_speed = "2deg/s"
antenna_max_acceleration = "1.5deg/s2"
```

and the followings are not:

```toml
[antenna]  # using table
max-speed = "2deg/s"  # not snake-case parameter name
MaxAcceleration = "1.5deg/s2"  # not snake-case nor lower case parameter name
```

### Attach parsers

If you want to read the parameter different from default type[^1] in Python, define
custom parser in `Configuration.__get_parser` in
[neclib/configuration.py](https://github.com/necst-telescope/neclib/blob/main/neclib/configuration.py).

[^1]: `list` (Array), `dict` (Inline table), `int` (Integer), `float` (Float), `bool`
(Boolean), `datetime.date` (Date), `datetime.datetime` (Datetime), `datetime.time`
(Time), and `str` (String).

## How to use the parameters

Just import `config` from `neclib` or `necst`, and you have access to all parameters
defined in config file as its attributes.

```python
>>> from neclib import config
>>> config.antenna_max_speed
'2deg/s'
```

If a parser is defined for the parameter, you'll get the parsed value.

```python
>>> config.antenna_max_speed
<Quantity 2 deg / s>
```

````{tip}
You can get a group of relative parameters using prefix.

```python
>>> antenna_params = config.antenna
>>> antenna_params
namespace(max_speed='2deg/s', max_acceleration='1.5deg/s2')
>>> antenna_params.max_speed
'2deg/s'
```

````

````{note}
You will get `None` on accessing nonexistent parameter or prefix.

```python
>>> print(config.undefined_parameters_a)
None
>>> print(config.undefined)
None
```

````
