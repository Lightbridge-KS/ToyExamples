"""Measure plugin: unit conversion in report text."""

import re

print("    (measure.py top level runs: importing a plugin executes its code)")

_MM = re.compile(r"(\d+(?:\.\d+)?)\s*mm\b")


def to_cm(text: str) -> str:
    """'12 mm' → '1.2 cm', everywhere in the text."""
    return _MM.sub(lambda m: f"{float(m[1]) / 10:g} cm", text)
