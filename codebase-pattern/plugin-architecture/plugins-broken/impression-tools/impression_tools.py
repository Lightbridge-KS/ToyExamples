"""Impression tools. Version 0.2.0 renamed uppercase() to shout(); plugin.toml was not updated."""


def extract(text: str) -> str:
    """Return the IMPRESSION section."""
    _, found, rest = text.partition("IMPRESSION:")
    return rest.strip() if found else "(no IMPRESSION section)"


def shout(text: str) -> str:
    return text.upper()
