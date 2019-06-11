import os
from enum import Enum

import pytest

from datacast import cast as _cast, apply_settings, EnvironConfig
from datacast.errors import *


class SimpleEnum(Enum):
    ONE = 1
    TWO = 2

    def __str__(self):
        return str(self.value)

class SimpleSchema:
    spam: int
    ham: bool = False
    rabbit: SimpleEnum = SimpleEnum.TWO


def test_cast():
    cast = lambda **data: _cast(data, SimpleSchema)
    assert cast(spam=1, ham=True) == dict(spam=1, ham=True, rabbit=SimpleEnum.TWO)
    assert (
        cast(spam=1, ham=True, rabbit=SimpleEnum.ONE) ==
        dict(spam=1, ham=True, rabbit=SimpleEnum.ONE)
    )


@pytest.fixture
def env_setup():
    fake_env = dict(SPAM='1', HAM='t', RABBIT='null')
    for k, v in fake_env.items():
        os.environ[k] = v
    yield
    for k in fake_env:
        if k in os.environ:
            del os.environ[k]


class SimpleEnvConfig(EnvironConfig):
    SPAM: int
    HAM: bool = False
    RABBIT: None = None
    KNIGHT: str = 'TestString'
    GRAIL: str = ''


def test_env(env_setup):
    conf = SimpleEnvConfig()
    assert conf.SPAM == 1
    assert conf.HAM is True
    assert conf.RABBIT == 'null'
    assert conf.KNIGHT == 'TestString'
    assert conf.GRAIL == ''


def test_env_fail(env_setup):
    del os.environ['SPAM']
    with pytest.raises(RequiredFieldError):
        SimpleEnvConfig()
    os.environ['SPAM'] = '2'
    config = SimpleEnvConfig()
    assert config.SPAM == 2
    assert (
        config._asdict() ==
        dict(SPAM=2, HAM=True, RABBIT='null', KNIGHT='TestString', GRAIL='')
    )


@apply_settings(
    on_extra='ignore',
    on_invalid='store',
    postcasters=[str],
    cast_defaults=True
)
class SchemaWithSettings:
    spam: int
    ham: bool = False
    rabbit: SimpleEnum = SimpleEnum.TWO


def test_cast_with_settings():
    cast = lambda **data: _cast(data, SchemaWithSettings)
    assert cast(spam=1, ham=True) == dict(spam='1', ham='True', rabbit='2')
    with pytest.raises(RequiredFieldError):
        cast(ham=True, rabbit=SimpleEnum.ONE)
    assert cast(spam='spam', f=1) == dict(spam='spam', ham='False', rabbit='2')


class SchemaOrig:
    spam: int


def test_raise_original():
    with pytest.raises(ValueError):
        _cast({'spam': 'spam'}, SchemaOrig, raise_original=True)
