*Datacast* is a Python package that validates and converts your data.

----

|pypi| |coverage| |license|

----

Basic Usage
-----------

Install with pip:

.. code:: bash

    pip install datacast


Define schema (can be any class with annotations) and use ``cast`` function.

.. code:: python

    from datacast import cast

    class SimpleSchema:
        zero: bool
        one: int
        two: str
        three: float = 0.3
        four: None = 'four'


    cast({'zero': 0, 'one': 1, 'two': 2, 'four': 5}, SimpleSchema)
    # {'zero': False, 'one': 1, 'two': '2', 'three': 0.3, 'four': 5}

Rules are simple:

-  Annotation is a *caster*, which will be called with the provided value, eg. ``bool(0)``.
-  If no default value is provided, the ``RequiredFieldError`` will be raised.
-  ``None`` in annotation means no casting.


Settings
---------

To be added.

.. |pypi| image:: https://img.shields.io/badge/version-0.1.0-orange.svg?style=flat-square
    :alt: Latest version released on PyPI

.. |coverage| image:: https://img.shields.io/badge/coverage-86%25-yellowgreen.svg?style=flat-square
    :alt: Test coverage

.. |license| image:: https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square
    :target: https://raw.githubusercontent.com/fatemonk/datacast/master/LICENSE
    :alt: Package license
