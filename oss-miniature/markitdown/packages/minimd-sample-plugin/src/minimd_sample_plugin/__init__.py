"""A third-party plugin, in miniature, shipped as its own package.

minimd never imports this module by name. Installing minimd-sample-plugin
writes a `minimd.plugin` entry point into the environment's package metadata
(see this package's pyproject.toml). minimd finds it there, and calls
register_converters() only when the user opts in with
MarkItDown(enable_plugins=True).

The dependency points one way, through one door: this module imports
minimd.plugin_api and nothing else from minimd.
"""

import configparser
import csv
import io
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, BinaryIO

from minimd.plugin_api import (
    PRIORITY_SPECIFIC_FILE_FORMAT,
    ConverterRegistry,
    DocumentConverter,
    DocumentConverterResult,
    StreamInfo,
)

# Below the built-ins' 0.0, so this runs first: it shadows a built-in without
# removing it. If it raises, dispatch falls through to the built-in.
PRIORITY_SHADOW = PRIORITY_SPECIFIC_FILE_FORMAT - 1.0


def register_converters(registry: ConverterRegistry, **kwargs: Any) -> None:
    """The entire plugin interface: minimd.plugin_api.Plugin."""
    registry.register_converter(IniConverter())  # a new format
    registry.register_converter(SniffingCsvConverter(), priority=PRIORITY_SHADOW)


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
            f"## {name}\n\n" + _table([["key", "value"], *parser[name].items()])
            for name in parser.sections()
        ]
        return DocumentConverterResult(markdown="\n\n".join(sections))


class SniffingCsvConverter(DocumentConverter):
    """Shadows the built-in CsvConverter: claims the same inputs, but detects
    ';' or tab delimiters instead of assuming ','."""

    def accepts(
        self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs: Any
    ) -> bool:
        # The built-in's claim, restated. Built-in converters aren't in
        # plugin_api, so subclassing CsvConverter would couple this package
        # to minimd's internals.
        extension = (stream_info.extension or "").lower()
        mimetype = (stream_info.mimetype or "").lower()
        return extension == ".csv" or mimetype.startswith("text/csv")

    def convert(
        self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs: Any
    ) -> DocumentConverterResult:
        text = file_stream.read().decode(stream_info.charset or "utf-8")
        dialect = csv.Sniffer().sniff(text, delimiters=",;\t")
        rows = list(csv.reader(io.StringIO(text), dialect))
        return DocumentConverterResult(markdown=_table(rows))


def _table(rows: Sequence[Sequence[str]]) -> str:
    """Render rows as a Markdown table; the first row is the header. (minimd
    has the same helper, but it isn't in plugin_api, so the plugin keeps its own.)"""
    header, *body = rows
    lines = ["| " + " | ".join(header) + " |", "|" + " --- |" * len(header)]
    lines += ["| " + " | ".join(row) + " |" for row in body]
    return "\n".join(lines)


if TYPE_CHECKING:  # the plugin vendor's own contract check, run by mypy
    import minimd_sample_plugin
    from minimd.plugin_api import Plugin

    _: Plugin = minimd_sample_plugin
