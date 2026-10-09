"""The seam between minimd and its plugins: everything a plugin may import.

Each name here is a promise to plugin vendors. Everything else in minimd,
built-in converters included, may change without notice.

Two Protocols face each other across the seam. Plugin is what the host
requires of a plugin; ConverterRegistry is the one thing the host lends it.
Neither side names the other's classes: each is checked by shape, statically
by a type checker, and (Plugin only, name only) at load time.
"""

from typing import Any, Protocol, runtime_checkable

from ._base_converter import DocumentConverter, DocumentConverterResult
from ._exceptions import MissingDependencyException
from ._stream_info import StreamInfo

# Where the host looks, and where a plugin's pyproject.toml registers itself.
ENTRY_POINT_GROUP = "minimd.plugin"

# Lower values are tried first.
PRIORITY_SPECIFIC_FILE_FORMAT = 0.0  # .csv, .yaml, ...
PRIORITY_GENERIC_FILE_FORMAT = 10.0  # catch-alls: any text, any zip


class ConverterRegistry(Protocol):
    """What the host lends a plugin: one method. MarkItDown satisfies it
    without naming it, and so does a test fake."""

    def register_converter(
        self,
        converter: DocumentConverter,
        *,
        priority: float = PRIORITY_SPECIFIC_FILE_FORMAT,
    ) -> None: ...


@runtime_checkable
class Plugin(Protocol):
    """What the host requires of a plugin. A module satisfies it with one
    top-level function of this shape, parameter names included."""

    def register_converters(
        self, registry: ConverterRegistry, **kwargs: Any
    ) -> None: ...


__all__ = [
    "ENTRY_POINT_GROUP",
    "PRIORITY_SPECIFIC_FILE_FORMAT",
    "PRIORITY_GENERIC_FILE_FORMAT",
    "Plugin",
    "ConverterRegistry",
    "DocumentConverter",
    "DocumentConverterResult",
    "StreamInfo",
    "MissingDependencyException",
]
