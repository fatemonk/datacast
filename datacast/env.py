import os

from .base import cast
from .caster import str_caster


class EnvironConfig:
    """Loads and casts named values from environ and stores them in instance."""

    def __init__(self):
        result = cast(os.environ, self.__class__,
                      on_extra='ignore', precasters=[str_caster])
        for k, v in result.items():
            setattr(self, k, v)
