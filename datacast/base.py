import os
from abc import ABC, abstractmethod
from collections import UserDict
from collections.abc import Iterable, Mapping, Set
from enum import Enum
from inspect import (_empty, isclass, isdatadescriptor,
                     ismethod, isroutine, signature)
from itertools import chain
from typing import Callable, Union, Type

from .errors import *


__all__ = [
    'cast', 'apply_settings', 'value_factory', 'str_caster',
    'Processor', 'Schema', 'Settings', 'Config', 'EnvironConfig'
]


class Option(str, Enum):
    """What to do when things go wrong."""
    IGNORE = 'ignore'  # value will be absent in result
    STORE = 'store'  # value will be stored in result
    RAISE = 'raise'  # corresponding exception will be raised
    CAST = 'cast'  # value will be casted with (pre & post)casters and stored
    # CAST works only for extra values!


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

    def create(self):
        """Main method, magic happens here."""
        result = self.settings.result_class()
        for field in self.schema:
            try:
                value = self._process_value(field)
            except SkipValue:
                continue
            result[field.name] = value
        if self.data:
            self._extra_values(result)
        return result

    def _process_value(self, field):
        """Get single value from input and process it."""
        value = self.data.pop(field.name, field.default)
        if value is missing:
            return self._bad_value_action(
                self.settings.on_missing,
                lambda: RequiredFieldError(field.name),
                lambda: self._missing_value()
            )
        try:
            caster = self._get_casters_chain(field.caster)
            return self._cast_value(value, caster)
        except InvalidCaster:
            raise
        except Exception as e:
            return self._bad_value_action(
                self.settings.on_invalid,
                lambda: CastError(value, e),
                lambda: value
            )

    def _extra_values(self, result):
        """What to do with extra values."""
        on_extra = self.settings.on_extra
        if on_extra == Option.STORE:
            result.update(self.data)
        elif on_extra == Option.CAST:
            caster = tuple(self._get_casters_chain(None))
            result.update({
                k: self._cast_value(v, caster) for k, v in self.data.items()
            })
        elif on_extra == Option.RAISE:
            raise ExtraValueError(self.data)
        elif on_extra != Option.IGNORE:
            raise InvalidOption(on_extra, 'extra')
        return

    def _bad_value_action(self, option, error, value):
        """What to do with bad values."""
        if option == Option.STORE:
            return value()
        if option == Option.RAISE:
            raise error()
        if option == Option.IGNORE:
            raise SkipValue
        raise InvalidOption(option)

    def _get_casters_chain(self, caster):
        """Get full casters chain with pre and postcasters."""
        precasters = self.settings.precasters or []
        postcasters = self.settings.postcasters or []
        if not (precasters or postcasters):
            return caster
        try:
            return chain(precasters, [caster], postcasters)
        except Exception as e:
            raise InvalidCaster(e)

    def _cast_value(self, value, caster):
        """Cast single value with casters chain."""
        if caster is None or isclass(caster) and isinstance(value, caster):
            return value
        if callable(caster):
            return caster(value)
        if self._is_ordered_sequence(caster):
            for _caster in caster:
                value = self._cast_value(value, _caster)
            return value
        raise InvalidCaster(caster, type(caster))

    def _is_ordered_sequence(self, caster):
        """Caster can be ordered sequence of another casters."""
        return (
            isinstance(caster, Iterable) and
            not isinstance(caster, (Mapping, Set))
        )

    def _missing_value(self):
        """Get or create missing based on settings."""
        value = self.settings.missing_value
        if (
            isinstance(value, value_factory) or
            callable(value) and not self.settings.store_callables
        ):
            return value()
        return value


class InputData(UserDict):
    """Transform object to dict."""

    def __init__(self, input_data):
        input_data = input_data or {}
        self.data = (
            dict(input_data) if isinstance(input_data, Mapping) else
            {k: v for k, v in iter_attrs(input_data, include_properties=True)}
        )


def iter_attrs(obj, include_properties=False):
    """Iterates through the attributes of object."""
    return (
        (k, v) for k, v in obj.__dict__.items()
        if not (
            k.startswith('_') or ismethod(v) or
            include_properties or isdatadescriptor(v)
        )
    )


class Schema:
    """Class or function with annotations as casters."""

    def __init__(self, obj):
        settings = getattr(obj, '__settings__', {})
        self.settings = SettingsBuilder(settings) if settings else None
        self.fields = {args[0]: Field(*args) for args in self._iter_obj(obj)}

    def _iter_obj(self, obj):
        """Iter over annotations of object."""
        if isclass(obj):
            if not hasattr(obj, '__annotations__'):
                return
            yield from self._iter_class(obj)
        elif isroutine(obj):
            yield from self._iter_function(obj)
        else:
            raise InvalidSchema(obj)

    def _iter_class(self, obj):
        for name, caster in obj.__annotations__.items():
            yield name, caster or _empty, getattr(obj, name, _empty)

    def _iter_function(self, obj):
        for name, param in signature(obj).parameters.items():
            if param.annotation is _empty:
                continue
            yield name, param.annotation, param.default

    def __iter__(self):
        yield from self.fields.values()

    def exclude(self, keys):
        """Exclude fields from process."""
        self.fields = {k: v for k, v in self.fields.items() if k not in keys}


class Field:
    """Field with name, caster and default value if provided."""

    def __init__(self, name, caster: Union[Callable, _empty, None], default):
        self.name = name
        self.caster = caster if caster is not _empty else None
        self.default = default if default is not _empty else missing


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

    def __new__(self, settings: Union[Type[Settings], Settings, dict]):
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


class Caster(ABC):
    """Function which transforms value into desireable one."""
    def __new__(cls, value):
        return object.__new__(cls)(value)

    @abstractmethod
    def __call__(self, value):
        """Must be implemented."""


class str_caster(Caster):
    """Casts string into most probable type based on its value."""
    VALID_BOOL_STR = {
        False: ('false', 'f', 'no', 'n', 'off', '0', ''),
        True: ('true', 't', 'yes', 'y', 'on', '1')
    }
    VALID_NONE_STR = {'none', 'null', 'nil'}

    def to_bool(value: str):
        value = value.strip().lower()
        for result, valid in str_caster.VALID_BOOL_STR.items():
            if value in valid:
                return result
        raise TypeError(value)

    def to_none(value: str):
        if value.lower() in str_caster.VALID_NONE_STR:
            return None
        raise TypeError(value)

    CASTERS = (int, float, to_none, to_bool)

    def __call__(self, value):
        for caster in self.CASTERS:
            try:
                return caster(value)
            except Exception as e:
                pass
        return value


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
        super().__init__(os.environ, on_extra='ignore', precasters=[str_caster])


class missing:
    """Marker object when value is missing."""

    def __repr__(self):
        return '<missing value>'


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
    return processor(input_data, schema, settings).create()
