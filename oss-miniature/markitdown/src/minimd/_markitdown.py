"""The orchestrator. Three jobs, and no knowledge of any file format:

1. Registry: converters with priorities; plugins add more.
2. Front doors: any source becomes (seekable stream, StreamInfo guesses).
3. Dispatch: ask each converter in priority order; the first success wins.
"""

import base64
import codecs
import io
import logging
import mimetypes
import os
import re
import traceback
import urllib.parse
from dataclasses import dataclass
from functools import cache
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any, BinaryIO
from warnings import warn

from ._base_converter import DocumentConverter, DocumentConverterResult
from ._exceptions import (
    FailedConversionAttempt,
    FileConversionException,
    UnsupportedFormatException,
)
from ._stream_info import StreamInfo
from .converters import CsvConverter, PlainTextConverter, YamlConverter, ZipConverter

log = logging.getLogger(__name__)  # the dispatch trace, at DEBUG level

# Lower values are tried first.
PRIORITY_SPECIFIC_FILE_FORMAT = 0.0  # .csv, .yaml, ...
PRIORITY_GENERIC_FILE_FORMAT = 10.0  # catch-alls: any text, any zip


# @cache: the first enable_plugins() loads, every later one reuses the list.
# The list is stored only once it is complete. (markitdown keeps it in a module
# global, set to [] before the loop, so a second thread can read it half-filled.)
@cache
def _load_plugins() -> list[Any]:
    """Find plugins through installed package metadata, once per process.

    A plugin that fails to import is skipped with a warning: a broken
    third-party package never takes the host down.
    """
    plugins = []
    for entry_point in entry_points(group="minimd.plugin"):
        try:
            plugins.append(entry_point.load())
        except Exception:
            tb = traceback.format_exc()
            warn(f"Plugin {entry_point.name!r} failed to load, skipping:\n{tb}")
    return plugins


@dataclass(frozen=True)
class ConverterRegistration:
    converter: DocumentConverter
    priority: float


class MarkItDown:
    def __init__(
        self,
        *,
        enable_builtins: bool = True,
        enable_plugins: bool = False,  # opt-in: third-party code runs only when asked
        **kwargs: Any,
    ):
        self._converters: list[ConverterRegistration] = []
        if enable_builtins:
            self.enable_builtins()
        if enable_plugins:
            self.enable_plugins(**kwargs)

    # -- 1. Registry --------------------------------------------------------

    def register_converter(
        self,
        converter: DocumentConverter,
        *,
        priority: float = PRIORITY_SPECIFIC_FILE_FORMAT,
    ) -> None:
        """Lower priority runs first. Among equals, the newest registration runs
        first (it goes to the front of the list, and the sort is stable)."""
        self._converters.insert(0, ConverterRegistration(converter, priority))

    def enable_builtins(self) -> None:
        # Generic before specific: with equal priorities, later registrations win.
        generic = PRIORITY_GENERIC_FILE_FORMAT
        self.register_converter(PlainTextConverter(), priority=generic)
        self.register_converter(ZipConverter(markitdown=self), priority=generic)
        self.register_converter(CsvConverter())
        self.register_converter(YamlConverter())

    def enable_plugins(self, **kwargs: Any) -> None:
        # The entire plugin interface: a module with register_converters(md).
        for plugin in _load_plugins():
            try:
                plugin.register_converters(self, **kwargs)
            except Exception:
                tb = traceback.format_exc()
                warn(f"Plugin {plugin!r} failed to register converters:\n{tb}")

    # -- 2. Front doors: every source becomes a seekable stream + base hints --

    def convert(
        self,
        source: str | Path | BinaryIO,
        *,
        stream_info: StreamInfo | None = None,
        **kwargs: Any,
    ) -> DocumentConverterResult:
        if isinstance(source, str) and source.startswith("data:"):
            return self.convert_uri(source, stream_info=stream_info, **kwargs)
        if isinstance(source, (str, Path)):
            return self.convert_local(source, stream_info=stream_info, **kwargs)
        if hasattr(source, "read"):
            return self.convert_stream(source, stream_info=stream_info, **kwargs)
        raise TypeError(f"Unsupported source type: {type(source).__name__}")

    def convert_local(
        self,
        path: str | Path,
        *,
        stream_info: StreamInfo | None = None,
        **kwargs: Any,
    ) -> DocumentConverterResult:
        path = str(path)
        base = StreamInfo(
            local_path=path,
            extension=os.path.splitext(path)[1],
            filename=os.path.basename(path),
        )
        if stream_info is not None:
            base = base.copy_and_update(stream_info)  # the caller's hints win
        with open(path, "rb") as file_stream:
            guesses = self._guesses(file_stream, base)
            return self._convert(file_stream, guesses, **kwargs)

    def convert_stream(
        self,
        stream: BinaryIO,
        *,
        stream_info: StreamInfo | None = None,
        **kwargs: Any,
    ) -> DocumentConverterResult:
        if not stream.seekable():  # dispatch rewinds between attempts, so buffer
            stream = io.BytesIO(stream.read())
        guesses = self._guesses(stream, stream_info or StreamInfo())
        return self._convert(stream, guesses, **kwargs)

    def convert_uri(
        self,
        uri: str,
        *,
        stream_info: StreamInfo | None = None,
        **kwargs: Any,
    ) -> DocumentConverterResult:
        """data: URIs only. markitdown handles file:, http: and https: the same
        way: pull hints out of the URI or the HTTP headers, then hand the bytes
        to convert_stream()."""
        header, _, payload = uri.removeprefix("data:").partition(",")
        mimetype, *params = header.split(";")
        if "base64" in params:
            data = base64.b64decode(payload)
        else:
            data = urllib.parse.unquote_to_bytes(payload)
        charset = next(
            (p.removeprefix("charset=") for p in params if p.startswith("charset=")),
            None,
        )
        base = StreamInfo(mimetype=mimetype or None, charset=charset)
        if stream_info is not None:
            base = base.copy_and_update(stream_info)
        return self.convert_stream(io.BytesIO(data), stream_info=base, **kwargs)

    # -- Guessing: don't trust the name alone ---------------------------------

    def _guesses(self, file_stream: BinaryIO, base: StreamInfo) -> list[StreamInfo]:
        """Combine the hints (name, caller, URI) with what the bytes say.

        Agree: one merged guess. Conflict: both, the hints first.
        """
        hinted = base
        if base.mimetype is None and base.extension:
            mimetype, _ = mimetypes.guess_type("x" + base.extension)
            hinted = hinted.copy_and_update(mimetype=mimetype)
        if base.extension is None and base.mimetype:
            extension = mimetypes.guess_extension(base.mimetype)
            hinted = hinted.copy_and_update(extension=extension)

        sniffed = _sniff(file_stream)
        if sniffed is None:
            return [hinted]
        if _compatible(base, sniffed):
            return [sniffed.copy_and_update(hinted)]  # the sniffer only fills gaps
        origin = StreamInfo(
            filename=base.filename, local_path=base.local_path, url=base.url
        )
        return [hinted, origin.copy_and_update(sniffed)]

    # -- 3. Dispatch: the first success wins ----------------------------------

    def _convert(
        self, file_stream: BinaryIO, guesses: list[StreamInfo], **kwargs: Any
    ) -> DocumentConverterResult:
        # Sort on every call, since plugins may register at any time. sorted() is
        # stable, so equal priorities keep their list order (newest first).
        registrations = sorted(self._converters, key=lambda r: r.priority)
        failed: list[FailedConversionAttempt] = []
        start = file_stream.tell()

        # The final, empty guess gives content-only converters a last chance.
        for n, stream_info in enumerate([*guesses, StreamInfo()], start=1):
            hints = (stream_info.extension, stream_info.mimetype, stream_info.charset)
            log.debug("guess %d: extension=%s mimetype=%s charset=%s", n, *hints)
            for registration in registrations:
                converter = registration.converter
                name = type(converter).__name__
                accepted = converter.accepts(file_stream, stream_info, **kwargs)
                assert file_stream.tell() == start, f"{name}.accepts() moved the stream"

                result, outcome = None, "no"
                if accepted:
                    try:
                        result = converter.convert(file_stream, stream_info, **kwargs)
                        outcome = "yes → ✓ converted"
                    except Exception as error:  # not fatal: record it, try the next
                        failed.append(FailedConversionAttempt(converter, error))
                        outcome = f"yes → ✗ {type(error).__name__}"
                    finally:
                        file_stream.seek(start)  # rewind for whoever is next
                log.debug("  %+5.1f  %-21s %s", registration.priority, name, outcome)

                if result is not None:
                    result.markdown = _normalize(result.markdown)
                    return result

        if failed:  # someone accepted it, and everyone who did failed
            raise FileConversionException(failed)
        raise UnsupportedFormatException("No converter accepted this input.")


def _sniff(file_stream: BinaryIO) -> StreamInfo | None:
    """Stand-in for magika, the deep-learning file-type detector: what do the
    bytes say, whatever the name claims? Peeks, then rewinds."""
    start = file_stream.tell()
    head = file_stream.read(4096)
    file_stream.seek(start)

    if head.startswith(b"PK\x03\x04"):
        return StreamInfo(mimetype="application/zip", extension=".zip")
    try:
        # An incremental decoder: a character cut in half at byte 4096 is fine.
        codecs.getincrementaldecoder("utf-8")().decode(head)
    except UnicodeDecodeError:
        return None  # binary we don't recognize: no opinion
    return StreamInfo(charset="utf-8")  # text, but which kind? The hints decide.


def _compatible(hints: StreamInfo, sniffed: StreamInfo) -> bool:
    """Conflict means a field both sides know, with different values."""
    for field in ("mimetype", "extension", "charset"):
        a, b = getattr(hints, field), getattr(sniffed, field)
        if a and b and a.lower() != b.lower():
            return False
    return True


def _normalize(markdown: str) -> str:
    """One output policy for every converter: no trailing spaces, no runs of
    blank lines. Cross-cutting rules live here, not in each converter."""
    markdown = "\n".join(line.rstrip() for line in markdown.splitlines())
    return re.sub(r"\n{3,}", "\n\n", markdown)
