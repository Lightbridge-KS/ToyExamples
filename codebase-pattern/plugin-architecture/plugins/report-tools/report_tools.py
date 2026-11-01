"""Report tools plugin: simple checks on report text."""


def word_count(text: str) -> str:
    return f"{len(text.split())} words"
