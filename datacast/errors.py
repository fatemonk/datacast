class DatacastException(Exception):
    """Base datacast error class."""

    def __init__(self, *data):
        message = f"{self.__doc__.replace('.','')}: {str(data)}"
        super().__init__(message)

class RequiredFieldError(DatacastException):
    """Field is required."""

class ExtraValueError(DatacastException):
    """Data contains extra values."""

class CastError(DatacastException):
    """Value cannot be casted."""

class InvalidCaster(DatacastException):
    """Not a valid caster."""

class InvalidSchema(DatacastException):
    """Object is not a valid schema."""

class InvalidOption(DatacastException):
    """Unknown of forbidden option."""
