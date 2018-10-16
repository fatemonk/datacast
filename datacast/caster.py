from abc import ABC, abstractmethod


class Caster(ABC):
    """Function which transforms value into desireable."""
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
