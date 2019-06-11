**Datacast** is a Python package that validates and converts your data.

--------------------------------------------

|pypi| |python_version| |coverage| |license|

--------------------------------------------

Basic Usage
-----------

Install with pip:

.. code:: bash

    pip install datacast


Define schema (can be any class with annotations) and use ``cast`` function.

.. code:: python

    from datacast import cast

    class SimpleSchema:
        one: int
        two: str
        three: (lambda x: x ** 2)
        zero: (int, bool)
        four: float = 0.4
        five: None = 'five'

    cast({'one': 1, 'two': 2, 'three': 3, 'zero': '0', 'five': 5}, SimpleSchema)
    # {'one': 1, 'two': '2', 'three': 9, 'zero': False, 'four': 0.4, 'five': 5}

Rules are simple:

-  Params without annotations will be ignored.
-  Annotation is a *caster*, which will be called with the provided value,
   eg. ``bool(0)``.
-  *Caster* is **any** callable. Functions, lambdas, classes etc.
-  It also can be list or tuple (or another iterable).
   Then it acts like a chain of *casters*, eg. ``int('0') -> bool(0) -> False``.
-  If there is no default value - param is required and
   will raise ``RequiredFieldError`` if not provided.
-  ``None`` in annotation means no casting.


Config
------
You can use ``Config`` class which acts like a schema AND stores result data.

.. code:: python

    from datacast import Config

    class SimpleConfig(Config):
        spam: bool
        ham: None
        rabbit: float = None

    config = SimpleConfig({'spam': 0, 'ham': 1})
    assert config.spam == False
    assert config.ham == 1
    assert config.rabbit == None
    assert config._asdict() == {'spam': False, 'ham': 1, 'rabbit': None}

Also there is ``EnvironConfig`` which loads input data from environment,
casts strings to appropriate types and ignores extra vars.

.. code:: python

    from datacast import EnvironConfig

    class SimpleEnvironConfig(EnvironConfig):
        SPAM: bool
        HAM: int
        RABBIT: str
        NONE_VAL: None

    os.environ['SPAM'] = '0'
    os.environ['HAM'] = '1'
    os.environ['RABBIT'] = '2'
    os.environ['NONE_VAL'] = 'null'
    config = SimpleEnvironConfig()
    assert config.SPAM == False
    assert config.HAM == 1
    assert config.RABBIT == '2'
    assert config.NONE_VAL == None

:Valid ``None`` strings: ``'none', 'null', 'nil'``
:Valid ``True`` strings: ``'true', 't', 'yes', 'y', 'on', '1'``
:Valid ``False`` strings: ``'false', 'f', 'no', 'n', 'off', '0', ''``

Case doesn't matter.


Settings
--------

You can specify various settings and apply them in a bunch of different ways.

.. code:: python

    from datacast import apply_settings, Settings

    @apply_settings(
        on_missing='store',
        missing_value=False
    )
    class SimpleSchema:
        ...

    # OR

    class SimpleSettings(Settings):
        on_missing = 'store'
        missing_value = False

    @apply_settings(SimpleSettings)
    class SimpleSchema:
        ...

    # OR pass it to the cast function or Config creation

    cast(input_data, SimpleSchema, settings=SimpleSettings)
    cast(input_data, SimpleSchema, on_missing='store', missing_value=False)
    Config(input_data, settings=SimpleSettings)
    Config(input_data, on_missing='store', missing_value=False)

    # OR use class attribute

    class SimpleSchema:
        __settings__ = SimpleSettings
        # OR
        __settings__ = {'on_missing': 'store', 'missing_value': False}
        ...


**List of settings**

===============  ============  ===============================================
Name             Default       Description
===============  ============  ===============================================
on_extra         ``'ignore'``  What to do with values that absent from schema.
on_invalid       ``'raise'``   What to do when casting has failed.
on_missing       ``'raise'``   What to do when value is missing but required.
missing_value    ``None``      What to store when value is missing.
store_callables  ``False``     If ``False`` - execute callable value on store.
result_class     ``dict``      Class which stores result data.
precasters       ``()``        Prepend additional casters.
postcasters      ``()``        Append additional casters.
cast_defaults    ``False``     Cast default values with full casters chain.
raise_original   ``False``     Raise original exception instead of CastError.
===============  ============  ===============================================

**Options for 'on_extra', 'on_invalid' and 'on_missing'**

:ignore: Value will be ignored and not be stored in the result.
:store: Value will be stored in the result as is. In case of ``on_missing`` it
        will store ``missing_value``.
:raise: Corresponding exception will be raised.
:cast: Value will be casted with precasters, postcasters and then stored.
       Works only with ``on_extra``!

With ``precasters`` and ``postcasters`` you will transform every caster in
schema into a chain, which starts and/or ends with those casters.


.. |pypi| image:: https://img.shields.io/pypi/v/datacast.svg?style=flat-square&label=version
    :target: https://pypi.org/project/datacast
    :alt: Latest version released on PyPI

.. |python_version| image:: https://img.shields.io/badge/python-%3E%3D3.3-blue.svg?style=flat-square
    :alt: Minimal Python version

.. |coverage| image:: https://img.shields.io/badge/coverage-86%25-yellowgreen.svg?style=flat-square
    :alt: Test coverage

.. |license| image:: https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square
    :target: https://raw.githubusercontent.com/fatemonk/datacast/master/LICENSE
    :alt: Package license
