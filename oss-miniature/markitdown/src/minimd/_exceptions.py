from dataclasses import dataclass
from typing import Any

MISSING_DEPENDENCY_MESSAGE = (
    "{converter} recognized the input as a {extension} file, but the library to "
    "read it is not installed. Install the optional dependency: "
    "pip install minimd[{feature}]"
)


class MarkItDownException(Exception):
    """Base of every error minimd raises."""


class MissingDependencyException(MarkItDownException):
    """A converter accepted the input, but its optional library is missing."""


class UnsupportedFormatException(MarkItDownException):
    """No converter accepted the input."""


@dataclass
class FailedConversionAttempt:
    """One converter that accepted the input, then raised."""

    converter: Any
    error: Exception


class FileConversionException(MarkItDownException):
    """Some converter accepted the input, and every one that did raised."""

    def __init__(self, attempts: list[FailedConversionAttempt]):
        self.attempts = attempts
        lines = [
            f" - {type(a.converter).__name__} threw {type(a.error).__name__}: {a.error}"
            for a in attempts
        ]
        super().__init__(
            f"File conversion failed after {len(attempts)} attempt(s):\n"
            + "\n".join(lines)
        )
