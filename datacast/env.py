import os

from .base import cast, dict_obj
from .caster import str_caster


class LoadEnviron(type):
    """Metaclass to load env vars on config import."""

    def __new__(cls, name, bases, dct):
        schema = super().__new__(cls, name, bases, dct)
        if not bases:
            return schema
        return cast(os.environ, schema)


class EnvironConfig(dict_obj):
    """Result class for store env vars."""


class EnvironSchema(metaclass=LoadEnviron):
    """Base schema class to create env configs."""

    __settings__ = {
        'precasters': [str_caster],
        'on_extra': 'ignore',
        'result_class': EnvironConfig
    }
