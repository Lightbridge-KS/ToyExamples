"""A third-party plugin, in miniature.

minimd never imports this module by name. It finds it through the
`minimd.plugin` entry point in pyproject.toml, and calls register_converters()
only when the user opts in with MarkItDown(enable_plugins=True).

The dependency points one way: plugin -> minimd, never back.
"""

import configparser
import csv
import io
from typing import Any, BinaryIO

from minimd import DocumentConverter, DocumentConverterResult, MarkItDown, StreamInfo
from minimd.converters import CsvConverter, markdown_table

# Below the built-ins' 0.0, so this runs first: it shadows a built-in without
# removing it. If it raises, dispatch falls through to the built-in.
PRIORITY_SHADOW = -1.0


def register_converters(markitdown: MarkItDown, **kwargs: Any) -> None:
    """The entire plugin interface."""
    markitdown.register_converter(IniConverter())  # a new format
    markitdown.register_converter(SniffingCsvConverter(), priority=PRIORITY_SHADOW)


class IniConverter(DocumentConverter):
    """A format the core has never heard of: each [section] becomes a table."""

    def accepts(
        self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs: Any
    ) -> bool:
        return (stream_info.extension or "").lower() == ".ini"

    def convert(
        self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs: Any
    ) -> DocumentConverterResult:
        parser = configparser.ConfigParser()
        parser.read_string(file_stream.read().decode(stream_info.charset or "utf-8"))
        sections = [
            f"## {name}\n\n" + markdown_table([["key", "value"], *parser[name].items()])
            for name in parser.sections()
        ]
        return DocumentConverterResult(markdown="\n\n".join(sections))


class SniffingCsvConverter(CsvConverter):
    """Shadows the built-in CsvConverter: detects ';' or tab delimiters instead
    of assuming ','. Inherits accepts(), so it claims exactly the same inputs."""

    def convert(
        self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs: Any
    ) -> DocumentConverterResult:
        text = file_stream.read().decode(stream_info.charset or "utf-8")
        dialect = csv.Sniffer().sniff(text, delimiters=",;\t")
        rows = list(csv.reader(io.StringIO(text), dialect))
        return DocumentConverterResult(markdown=markdown_table(rows))
