from dataclasses import dataclass
from typing import Any, BinaryIO

from ._stream_info import StreamInfo


@dataclass
class DocumentConverterResult:
    """What every converter returns: Markdown, plus an optional title."""

    markdown: str
    title: str | None = None

    def __str__(self) -> str:
        return self.markdown


class DocumentConverter:
    """The whole converter contract: two methods with the same signature.

    accepts() is a cheap yes/no, decided from the hints in `stream_info`. If it
    peeks at the bytes, it must put `file_stream` back where it found it.

    convert() does the real work, and may raise: the dispatcher records the
    failure and moves on to the next candidate.
    """

    def accepts(
        self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs: Any
    ) -> bool:
        raise NotImplementedError

    def convert(
        self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs: Any
    ) -> DocumentConverterResult:
        raise NotImplementedError
