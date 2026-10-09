#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Proof that classic.py and modern.py behave the same: their transcripts must match.

Run:  uv run compare.py
"""
import classic
import modern

classic_out, modern_out = classic.run(), modern.run()
assert classic_out == modern_out, "transcripts differ:\n" + "\n".join(
    f"{c!r:45} | {m!r}" for c, m in zip(classic_out, modern_out) if c != m
)
print("\n".join(modern_out))
print(f"\n✓ classic.py and modern.py produced the same {len(modern_out)}-line transcript")
