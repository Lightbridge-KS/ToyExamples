"""The built-in converters.

The core knows them only through the DocumentConverter contract, and
MarkItDown.enable_builtins() registers them with the same public
register_converter() a plugin uses. Built-ins get no back door.
"""

import csv
import io
import os
import zipfile
from typing import TYPE_CHECKING, Any, BinaryIO

from ._base_converter import DocumentConverter, DocumentConverterResult
from ._exceptions import (
    MISSING_DEPENDENCY_MESSAGE,
    FileConversionException,
    MissingDependencyException,
    UnsupportedFormatException,
)
from ._stream_info import StreamInfo

if TYPE_CHECKING:  # a type hint only: a runtime import would be circular
    from ._markitdown import MarkItDown

# An optional dependency: a failed import is remembered, not raised. minimd
# still imports and works; only YamlConverter.convert() fails, when it's needed.
try:
    import yaml
except ImportError as error:
    _yaml_import_error: ImportError | None = error
else:
    _yaml_import_error = None


def _hinted(
    stream_info: StreamInfo, extensions: tuple[str, ...], mime_prefixes: tuple[str, ...]
) -> bool:
    """The accepts() test nearly every converter uses: a known extension or MIME type.

    (markitdown repeats these lines inside each converter.)
    """
    extension = (stream_info.extension or "").lower()
    mimetype = (stream_info.mimetype or "").lower()
    return extension in extensions or mimetype.startswith(mime_prefixes)


def markdown_table(rows: list[list[str]]) -> str:
    """Render rows as a Markdown table; the first row is the header."""
    header, *body = rows
    lines = ["| " + " | ".join(header) + " |", "|" + " --- |" * len(header)]
    lines += ["| " + " | ".join(row) + " |" for row in body]
    return "\n".join(lines)


class PlainTextConverter(DocumentConverter):
    """Generic catch-all: anything that decodes as text."""

    def accepts(
        self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs: Any
    ) -> bool:
        # A charset means the sniffer already found the bytes to be text.
        if stream_info.charset is not None:
            return True
        return _hinted(stream_info, (".txt", ".md"), ("text/",))

    def convert(
        self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs: Any
    ) -> DocumentConverterResult:
        text = file_stream.read().decode(stream_info.charset or "utf-8")
        return DocumentConverterResult(markdown=text)


class CsvConverter(DocumentConverter):
    """A specific format: comma-separated rows become a Markdown table."""

    def accepts(
        self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs: Any
    ) -> bool:
        return _hinted(stream_info, (".csv",), ("text/csv",))

    def convert(
        self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs: Any
    ) -> DocumentConverterResult:
        text = file_stream.read().decode(stream_info.charset or "utf-8")
        rows = list(csv.reader(io.StringIO(text)))
        return DocumentConverterResult(markdown=markdown_table(rows))


class YamlConverter(DocumentConverter):
    """A specific format behind an optional dependency: minimd[yaml]."""

    def accepts(
        self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs: Any
    ) -> bool:
        # No dependency check here: accepts() says "this is mine", convert() says
        # "and I can't", so the user learns which extra to install.
        return _hinted(
            stream_info, (".yaml", ".yml"), ("application/yaml", "text/yaml")
        )

    def convert(
        self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs: Any
    ) -> DocumentConverterResult:
        if _yaml_import_error is not None:
            raise MissingDependencyException(
                MISSING_DEPENDENCY_MESSAGE.format(
                    converter=type(self).__name__, extension=".yaml", feature="yaml"
                )
            ) from _yaml_import_error

        data = yaml.safe_load(file_stream)
        lines = [f"- **{key}**: {value}" for key, value in data.items()]
        return DocumentConverterResult(markdown="\n".join(lines))


class ZipConverter(DocumentConverter):
    """Recursion through the registry: each member goes back through MarkItDown,
    so a zip can hold anything any converter, plugins included, can read."""

    def __init__(self, *, markitdown: "MarkItDown"):
        self._markitdown = markitdown

    def accepts(
        self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs: Any
    ) -> bool:
        return _hinted(stream_info, (".zip",), ("application/zip",))

    def convert(
        self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs: Any
    ) -> DocumentConverterResult:
        sections = []
        with zipfile.ZipFile(file_stream) as archive:
            for name in archive.namelist():
                member_info = StreamInfo(
                    extension=os.path.splitext(name)[1], filename=os.path.basename(name)
                )
                try:
                    result = self._markitdown.convert_stream(
                        io.BytesIO(archive.read(name)), stream_info=member_info
                    )
                except (UnsupportedFormatException, FileConversionException):
                    continue  # one unreadable member doesn't sink the archive
                sections.append(f"## File: {name}\n\n{result.markdown}")
        return DocumentConverterResult(markdown="\n\n".join(sections))
