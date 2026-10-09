"""Seven scenes through minimd's dispatch loop, with the trace switched on.

uv run --exact demo.py                   # minimd alone: scene 7 finds no plugin
uv run --exact --extra plugins demo.py   # + the plugin package: scene 7 changes
uv run --exact --extra yaml demo.py      # + minimd[yaml]: scene 5 changes

(--exact makes uv remove a package again when its extra isn't asked for.)
"""

import inspect
import io
import logging
import sys
import urllib.parse
import zipfile
from dataclasses import asdict
from importlib.metadata import entry_points
from pathlib import Path

from minimd import MarkItDown, MarkItDownException, StreamInfo
from minimd.plugin_api import ENTRY_POINT_GROUP

SAMPLES = Path(__file__).parent / "samples"


def main() -> None:
    show_dispatch_trace()
    md = MarkItDown()  # built-ins only: the default
    csv_text = (SAMPLES / "report.csv").read_text()

    scene("1 · Specific beats generic")
    # CsvConverter (0.0) and PlainTextConverter (10.0) would both accept a .csv.
    # The lower number is asked first, so the generic one is never reached.
    first = convert(md, SAMPLES / "report.csv")

    scene("2 · Three doors, one dispatch")
    # A path, a stream with a hint, a data: URI: each door builds the same
    # (stream, StreamInfo) pair, so the same converter runs and the output matches.
    second = convert(
        md, io.BytesIO(csv_text.encode()), stream_info=StreamInfo(extension=".csv")
    )
    third = convert(md, "data:text/csv;charset=utf-8," + urllib.parse.quote(csv_text))
    print(f"\nall three identical: {first == second == third}")

    scene("3 · No name? Ask the bytes")
    # A bare stream has no hints at all. The sniffer sees a zip header, and
    # ZipConverter sends each member back through the same dispatch (indented).
    convert(md, io.BytesIO(make_zip()))

    scene("4 · The name lies")
    # Hint says .txt, bytes say zip: two guesses, the hint's first. Plain text
    # fails to decode, the failure is recorded, and guess 2 succeeds.
    convert(
        md,
        io.BytesIO(make_zip()),
        stream_info=StreamInfo(extension=".txt", filename="notes.txt"),
    )

    scene("5 · A missing library is a soft failure")
    # YamlConverter claims .yaml but can't import yaml. Not fatal: the next
    # candidate (plain text) returns the raw file, silently. Rerun with the extra.
    convert(md, SAMPLES / "config.yaml")

    scene("6 · Two ways to fail")
    # A zip header with nothing behind it: accepted, then failed → FileConversionException.
    convert(
        md,
        io.BytesIO(b"PK\x03\x04 cut short"),
        stream_info=StreamInfo(extension=".zip"),
    )
    # Bytes nobody claims → UnsupportedFormatException.
    convert(
        md, io.BytesIO(b"\x00\xff\xfe\xfd"), stream_info=StreamInfo(extension=".bin")
    )

    scene("7 · Plugins: a separate package, discovered, opted into")
    # minimd knows only the group name. The entry point comes from the plugin
    # package's own metadata, so installing that package is the whole wiring.
    found = entry_points(group=ENTRY_POINT_GROUP)
    for ep in found:
        print(f"entry point {ep.name!r} → {ep.value}, installed by {ep.dist.name}")
    if not found:
        print(
            "no plugin installed: rerun with `uv run --exact --extra plugins demo.py`"
        )
        return
    with_plugins = MarkItDown(enable_plugins=True)
    # The plugin's SniffingCsvConverter (-1.0) shadows the built-in CsvConverter (0.0).
    convert(md, SAMPLES / "supplies.csv")
    convert(with_plugins, SAMPLES / "supplies.csv", name="with_plugins")
    # The plugin's IniConverter (0.0) adds a format; without it, plain text catches .ini.
    convert(md, SAMPLES / "settings.ini")
    convert(with_plugins, SAMPLES / "settings.ini", name="with_plugins")


def convert(md: MarkItDown, source, *, name: str = "md", **kwargs) -> str | None:
    """Convert, print the trace and the result, and return the Markdown."""
    print(f"\n>>> {name}.convert({describe(source, **kwargs)})")
    try:
        markdown = md.convert(source, **kwargs).markdown
    except MarkItDownException as error:
        print(f"!!! {type(error).__name__}: {error}")
        return None
    print("\n".join("  │ " + line for line in markdown.splitlines()))
    return markdown


def describe(source, stream_info: StreamInfo | None = None) -> str:
    if isinstance(source, Path):
        text = f"samples/{source.name}"
    elif isinstance(source, io.BytesIO):
        text = f"<{source.getbuffer().nbytes} bytes>"
    else:
        text = repr(source[:40] + "…")
    if stream_info is not None:
        fields = ", ".join(f"{k}={v!r}" for k, v in asdict(stream_info).items() if v)
        text += f", stream_info=StreamInfo({fields})"
    return text


def make_zip() -> bytes:
    """A csv, a txt, and a binary nobody can read, deflated."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(SAMPLES / "report.csv", "report.csv")
        archive.writestr("readme.txt", "Monthly study volumes. See report.csv.")
        archive.writestr("scan.bin", bytes(range(128, 256)))
    return buffer.getvalue()


def scene(title: str) -> None:
    print(f"\n\n━━ {title} " + "━" * (66 - len(title)))


class IndentByDepth(logging.Filter):
    """Indent each trace line by how deeply dispatch is nested: a zip member's
    dispatch runs inside the zip's own. (Presentation only; the core stays flat.)"""

    def filter(self, record: logging.LogRecord) -> bool:
        depth = sum(frame.function == "_convert" for frame in inspect.stack(0))
        record.msg = "    " * depth + record.msg
        return True


def show_dispatch_trace() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.addFilter(IndentByDepth())
    logger = logging.getLogger("minimd")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)


if __name__ == "__main__":
    main()
