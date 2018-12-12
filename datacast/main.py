"""Datacast is a Python package that validates and converts your data.

Define schema (can be any class with annotations) and use cast function.

Example:
    from datacast import cast

    class Schema:
        one: int
        two: str
        three: (lambda x: x ** 2)
        zero: (int, bool)
        four: float = 0.4
        five: None = 'five'

    cast({'one': 1, 'two': 2, 'three': 3, 'zero': '0', 'five': 5}, Schema)
    # {'one': 1, 'two': '2', 'three': 9, 'zero': False, 'four': 0.4, 'five': 5}

Rules:
    - Params without annotations will be ignored.
    - Annotation is a caster, which will be called with the provided value,
      eg. bool(0).
    - Caster is any callable. Functions, lambdas, classes etc.
    - It also can be list or tuple (or another iterable). Then it acts like
      a chain of casters, eg. int('0') -> bool(0) -> False.
    - If there is no default value - param is required and will raise
      RequiredFieldError if not provided.
    - None in annotation means no casting.
"""
import os
from abc import ABC, abstractmethod
from collections import UserDict
from collections.abc import Iterable, Mapping, Set
from enum import Enum
from inspect import (_empty, isclass, isdatadescriptor,
                     ismethod, isroutine, signature)
from itertools import chain
from typing import Any, Callable, Union, Type

from .errors import (RequiredFieldError, ExtraValueError, CastError,
                     InvalidCaster, InvalidSchema, InvalidOption)


__all__ = [
    'cast', 'apply_settings', 'value_factory', 'str_caster',
    'Processor', 'Schema', 'Settings', 'Config', 'EnvironConfig'
]

VALID_NONE_STR = {'none', 'null', 'nil', ''}
VALID_BOOL_STR = {
    False: ('false', 'f', 'no', 'n', 'off', '0', ''),
    True: ('true', 't', 'yes', 'y', 'on', '1')
}


class Option(str, Enum):
    """What to do when things go wrong."""
    IGNORE = 'ignore'  # value will be absent in result
    STORE = 'store'  # value will be stored in result
    RAISE = 'raise'  # corresponding exception will be raised
    CAST = 'cast'  # value will be casted with pre-/postcasters and stored
    # CAST works only for extra values!


class missing:
    """Marker object when value is missing."""

    def __repr__(self):
        return '<missing value>'


class Processor:
    """Creates valid data based on input data, schema and settings."""
    __cache__ = {}

    def __init__(self, input_data, schema, settings=None):
        self.data = InputData(input_data)
        self.schema = self._get_schema(schema)
        self.settings = self.schema.settings or SettingsBuilder(settings)

    def _get_schema(self, obj):
        if isinstance(obj, Schema):
            return obj
        return self.__cache__.setdefault(id(obj), Schema(obj))

    def run(self):
        """Main method, magic happens here."""
        result = self.settings.result_class()
        for field in self.schema:
            try:
                value = self._process_value(field)
            except SkipValue:
                continue
            result[field.name] = value
        if self.data:
            self._process_extra_values(result)
        return result

    def _process_value(self, field):
        """Get single value from input and process it."""
        value = self.data.pop(field.name, field.default)
        if value is missing:
            return self._process_missing_value(field.name)
        try:
            caster = self._get_casters_chain(field.caster)
            return self._cast_value(value, caster)
        except InvalidCaster:
            raise
        except Exception as exc:
            return self._process_invalid_value(value, exc)

    def _process_missing_value(self, field_name):
        option = self.settings.on_missing
        if option in (Option.STORE, Option.CAST):
            return self._missing_value()
        if option == Option.RAISE:
            raise RequiredFieldError(field_name)
        if option == Option.IGNORE:
            raise SkipValue
        raise InvalidOption(option)

    def _process_invalid_value(self, value, exc):
        option = self.settings.on_invalid
        if option == Option.STORE:
            return value
        if option == Option.RAISE:
            raise CastError(value, exc)
        if option == Option.IGNORE:
            raise SkipValue
        raise InvalidOption(option)

    def _process_extra_values(self, result):
        """What to do with extra values."""
        option = self.settings.on_extra
        if option == Option.STORE:
            result.update(self.data)
        elif option == Option.CAST:
            caster = tuple(self._get_casters_chain(None))
            result.update({key: self._cast_value(value, caster)
                           for key, value in self.data.items()})
        elif option == Option.RAISE:
            raise ExtraValueError(self.data)
        elif option != Option.IGNORE:
            raise InvalidOption(option, 'extra')

    def _get_casters_chain(self, caster):
        """Get full casters chain with pre and postcasters."""
        precasters = self.settings.precasters or []
        postcasters = self.settings.postcasters or []
        if not (precasters or postcasters):
            return caster
        try:
            return chain(precasters, [caster], postcasters)
        except Exception as exc:
            raise InvalidCaster(exc)

    def _cast_value(self, value, caster):
        """Cast single value with casters chain."""
        if caster is None or isclass(caster) and type(value) == caster:
            return value
        if callable(caster):
            return caster(value)
        if is_ordered_sequence(caster):
            for _caster in caster:
                value = self._cast_value(value, _caster)
            return value
        raise InvalidCaster(caster, type(caster))

    def _missing_value(self):
        """Get or create missing based on settings."""
        value = self.settings.missing_value
        if (isinstance(value, value_factory)
                or callable(value) and not self.settings.store_callables):
            return value()
        return value


def is_ordered_sequence(caster):
    """Caster can be ordered sequence of another casters."""
    return (isinstance(caster, Iterable)
            and not isinstance(caster, (Mapping, Set)))


class InputData(UserDict):
    """Transform object to dict."""

    def __init__(self, input_data):
        input_data = input_data or {}
        super().__init__(
            dict(input_data) if isinstance(input_data, Mapping) else
            {k: v for k, v in iter_attrs(input_data, include_properties=True)}
        )


def iter_attrs(obj, include_properties=False):
    """Iterates through the attributes of object."""
    for key, value in obj.__dict__.items():
        if key.startswith('_') or ismethod(value):
            continue
        if not include_properties and isdatadescriptor(value):
            continue
        yield key, value


class Caster(ABC):
    """Function which transforms value into desireable one."""
    def __new__(cls, value):
        return object.__new__(cls)(value)

    @abstractmethod
    def __call__(self, value):
        """Must be implemented."""


def str_to_none(value: str):
    """Returns None if string is none-like word."""
    value = value.strip().lower()
    if value in VALID_NONE_STR:
        return None
    raise TypeError(value)


def str_to_bool(value: str):
    """Returns True or False if string is bool-like word."""
    value = value.strip().lower()
    for result, valid in VALID_BOOL_STR.items():
        if value in valid:
            return result
    raise TypeError(value)


class str_caster(Caster):
    """Casts string into most probable type based on its value."""
    CASTERS = (float, str_to_none, str_to_bool)

    def __call__(self, value):
        for caster in self.CASTERS:
            try:
                return caster(value)
            except Exception:
                pass
        return value


CasterUnion = Union[Caster, Callable, _empty, None]


class Schema:
    """Class or function with annotations as casters."""

    def __init__(self, obj):
        settings = getattr(obj, '__settings__', {})
        self.settings = SettingsBuilder(settings) if settings else None
        self.fields = {args[0]: Field(*args)
                       for args in iter_object_annotations(obj)}

    def __iter__(self):
        yield from self.fields.values()

    def exclude(self, keys):
        """Exclude fields from process."""
        self.fields = {k: v for k, v in self.fields.items() if k not in keys}


class Field:
    """Field with name, caster and default value if provided."""

    def __init__(self, name: str, caster: CasterUnion, default: Any = missing):
        self.name = name
        self.caster = caster if caster is not _empty else None
        self.default = default if default is not _empty else missing


def iter_object_annotations(obj) -> (str, CasterUnion, Any):
    """Iter over annotations of object."""
    if isclass(obj):
        yield from iter_class_annotations(obj)
    elif isroutine(obj):
        yield from iter_function_annotations(obj)
    else:
        raise InvalidSchema(obj)


def iter_class_annotations(obj):
    """Iterates over annotations of class and it's default values."""
    fields = set()
    for cls in obj.__mro__:
        for name, caster in getattr(cls, '__annotations__', {}).items():
            if name in fields:
                continue
            fields.add(name)
            yield name, caster or _empty, getattr(cls, name, _empty)


def iter_function_annotations(obj):
    """Iterates over annotations of function and it's default values."""
    for name, param in signature(obj).parameters.items():
        if param.annotation is _empty:
            continue
        yield name, param.annotation, param.default


class Settings:
    """Various settings to modify processor's behavior."""
    on_extra = Option.IGNORE  # what to do with extra values
    on_invalid = Option.RAISE  # what to do when value is invalid
    on_missing = Option.RAISE  # what to do when value is missing but required
    missing_value = None  # what to store when value is missing
    store_callables = False  # can result store callables
    result_class = dict  # class which stores result data
    precasters = ()  # prepend additional casters
    postcasters = ()  # append additional casters

    def __init__(self, **settings):
        for name, _ in iter_attrs(self.__class__):
            value = settings.pop(name, None)
            if value:
                setattr(self, name, value)
            if not settings:
                break


class SettingsBuilder:
    """Creates settings from dict or another Settings object or class."""

    def __new__(cls, settings: Union[Type[Settings], Settings, dict]):
        if isclass(settings) and issubclass(settings, Settings):
            return settings()
        if isinstance(settings, Settings):
            return settings
        if not settings:
            return Settings()
        _settings = settings.pop('settings', None)
        if isinstance(_settings, Settings):
            return _settings
        return Settings(**settings)


class Config:
    """Schema and result type in one class.

    On __init__ casts input_data using itself like a schema.

    Args:
        input_data - any dict or object with public attributes;
    Kwargs:
        processor - custom Processor class for process input data;
        settings - various casting settings;
    """

    def __init__(self, input_data, processor=None, **settings):
        self.__keys__ = []
        result = cast(input_data, self.__class__, processor, **settings)
        for key, value in result.items():
            self.__keys__.append(key)
            setattr(self, key, value)

    def _asdict(self) -> dict:
        return {key: getattr(self, key) for key in self.__keys__}


class EnvironConfig(Config):
    """Loads input_data from env and casts values into most probable type."""

    def __init__(self):
        super().__init__(
            os.environ,
            processor=EnvironProcessor,
            on_extra='ignore'
        )


class EnvironProcessor(Processor):
    """Process logic strings from env."""
    logic_casters = {
        None: str_to_none,
        bool: str_to_bool
    }

    def _cast_value(self, value, caster):
        if isinstance(value, str) and caster in self.logic_casters:
            caster = self.logic_casters[caster]
        return super()._cast_value(value, caster)


class SkipValue(Exception):
    """No value to store, skip."""


class value_factory:
    """Generates value at runtime.

    Can be used as a default value."""

    def __init__(self, factory: Callable):
        self.factory = factory

    def __call__(self):
        return self.factory()


def apply_settings(settings: Union[Settings, dict] = None, **options):
    """Decorate class or method to apply settings."""
    def wrapper(schema):
        schema.__settings__ = SettingsBuilder(settings or options)
        return schema
    return wrapper


def cast(input_data, schema, processor=None, **settings):
    """Casts data based on schema and settings.

    Args:
        input_data - any dict or object with public attributes;
        schema - any class or function with annotations;
    Kwargs:
        processor - custom Processor class for process input data;
        settings - various casting settings;
    """
    processor = processor or Processor
    return processor(input_data, schema, settings).run()
