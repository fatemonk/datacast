import os
from enum import Enum

import pytest

from datacast import cast as _cast, apply_settings
from datacast.caster import str_caster
from datacast.env import EnvironSchema
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
def os_env():
    os.environ['SPAM'] = '1'
    os.environ['HAM'] = 't'
    os.environ['RABBIT'] = 'null'


@pytest.fixture
def simple_env_conf():
    def wrapper():
        class SimpleEnvConfig(EnvironSchema):
            SPAM: int
            HAM: bool = False
            RABBIT: None = None
            KNIGHT: str = 'TestString'
        return SimpleEnvConfig
    return wrapper


def test_env(os_env, simple_env_conf):
    conf = simple_env_conf()
    assert conf.SPAM == 1
    assert conf.HAM is True
    assert conf.RABBIT is None
    assert conf.KNIGHT == 'TestString'


def test_env_fail(os_env, simple_env_conf):
    del os.environ['SPAM']
    with pytest.raises(RequiredFieldError):
        simple_env_conf()


@apply_settings(
    on_extra='ignore',
    on_invalid='store',
    postcasters=[str]
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
    assert cast(spam='spam') == dict(spam='spam', ham='False', rabbit='2')
    assert cast(spam='spam', f=1) == dict(spam='spam', ham='False', rabbit='2')
