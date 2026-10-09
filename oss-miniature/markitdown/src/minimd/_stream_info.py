from dataclasses import asdict, dataclass


@dataclass(kw_only=True, frozen=True)
class StreamInfo:
    """Everything we *believe* about a byte stream. Any field may be None.

    Frozen: a guess is never edited in place, only copied with updates, so one
    guess can safely fan out into several.
    """

    mimetype: str | None = None
    extension: str | None = None
    charset: str | None = None
    filename: str | None = None  # from a path, a URL, or a Content-Disposition header
    local_path: str | None = None  # if read from disk
    url: str | None = None  # if fetched

    def copy_and_update(self, *others: "StreamInfo", **fields) -> "StreamInfo":
        """Return a copy. The non-None fields of `others`, then `fields`, win."""
        merged = asdict(self)
        for other in others:
            merged.update({k: v for k, v in asdict(other).items() if v is not None})
        merged.update(fields)
        return StreamInfo(**merged)
