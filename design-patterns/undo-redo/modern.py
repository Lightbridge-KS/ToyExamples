#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Undo/redo, MODERN shape: the same three patterns, absorbed by immutable values.

    Command   -> a frozen dataclass: data saying what to do, interpreted by one apply() function
    Memento   -> the previous value itself; an immutable str can't change behind anyone's back
    Composite -> Macro holds commands, and apply() folds over them with reduce()

Open next to classic.py: the scenario is the same and so is the transcript.

Run:  uv run modern.py
"""
from dataclasses import dataclass
from functools import reduce
from typing import assert_never


# ── Command: plain data. No receiver inside, no execute(), no undo() ─────────

@dataclass(frozen=True)
class Insert:
    pos: int
    text: str


@dataclass(frozen=True)
class Delete:
    pos: int
    length: int


@dataclass(frozen=True)
class Revert:
    to: str                                     # the checkpoint is just the old text


# ── Composite: a command made of commands ────────────────────────────────────

@dataclass(frozen=True)
class Macro:
    steps: tuple["Command", ...]


type Command = Insert | Delete | Revert | Macro


def apply(text: str, command: Command) -> str:
    """The only code that knows what a command does: (old text, command) -> new text."""
    match command:
        case Insert(pos, s):
            return text[:pos] + s + text[pos:]
        case Delete(pos, length):
            return text[:pos] + text[pos + length:]
        case Revert(to):
            return to
        case Macro(steps):
            return reduce(apply, steps, text)   # the Composite: fold over the children
        case _:
            assert_never(command)


# ── Memento + invoker: a history is three values, and undo means "step back" ─
# No command knows its inverse. Undo doesn't run anything; it just looks back.

@dataclass(frozen=True)
class History:
    present: str = ""
    past: tuple[str, ...] = ()
    future: tuple[str, ...] = ()

    def do(self, command: Command) -> "History":
        # Leaving `future` at its default () drops the redo branch.
        return History(apply(self.present, command), (*self.past, self.present))

    def undo(self) -> "History":
        if not self.past:
            return self
        return History(self.past[-1], self.past[:-1], (self.present, *self.future))

    def redo(self) -> "History":
        if not self.future:
            return self
        return History(self.future[0], (*self.past, self.present), self.future[1:])


# ── Composition root: commands are values, so nothing needs binding ──────────

def run() -> list[str]:
    out: list[str] = []
    history = History()

    def show(verb: str, label: str = "") -> None:
        out.append(f"{verb:<5} {label:<34} → {history.present!r}")

    history = history.do(Insert(0, "hello"))
    show("do", "insert 'hello'")
    history = history.do(Insert(5, " world"))
    show("do", "insert ' world'")
    checkpoint = history.present                # the Memento: keep a reference, nothing more
    show("save", "checkpoint")
    history = history.do(Macro((Delete(0, 5), Insert(0, "goodbye"))))
    show("do", "macro: 'hello' → 'goodbye'")
    history = history.do(Insert(13, "!"))
    show("do", "insert '!'")
    history = history.do(Revert(checkpoint))
    show("do", "revert to checkpoint")
    for _ in range(3):
        history = history.undo()
        show("undo")
    history = history.redo()
    show("redo")
    history = history.do(Insert(13, "?"))
    show("do", "insert '?' (drops the redo branch)")
    history = history.redo()
    show("redo", "(nothing to redo)")
    return out


if __name__ == "__main__":
    print("\n".join(run()))
