#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Undo/redo, CLASSIC shape: three GoF patterns as the book draws them.

    Command   : each edit is an object with execute() and undo(); History runs and stacks them
    Memento   : Editor.save() hands out an opaque snapshot that only Editor can restore
    Composite : Macro is a Command made of Commands, so a group of edits undoes as one step

Open next to modern.py: the scenario is the same and so is the transcript.

Run:  uv run classic.py
"""
from abc import ABC, abstractmethod


# ── Receiver and Memento originator: the object that owns the text ───────────

class Editor:
    def __init__(self) -> None:
        self.text = ""

    def insert(self, pos: int, s: str) -> None:
        self.text = self.text[:pos] + s + self.text[pos:]

    def delete(self, pos: int, length: int) -> str:
        removed = self.text[pos:pos + length]
        self.text = self.text[:pos] + self.text[pos + length:]
        return removed

    def save(self) -> "Memento":
        return Memento(self.text)

    def restore(self, memento: "Memento") -> None:
        self.text = memento._state              # only the originator looks inside


# ── Memento: a snapshot that others hold but never open ──────────────────────

class Memento:
    def __init__(self, state: str) -> None:
        self._state = state


# ── Command: a request turned into an object that can also reverse itself ────

class Command(ABC):
    @abstractmethod
    def execute(self) -> None: ...

    @abstractmethod
    def undo(self) -> None: ...


class Insert(Command):
    def __init__(self, editor: Editor, pos: int, text: str) -> None:
        self._editor, self._pos, self._text = editor, pos, text

    def execute(self) -> None:
        self._editor.insert(self._pos, self._text)

    def undo(self) -> None:
        self._editor.delete(self._pos, len(self._text))


class Delete(Command):
    def __init__(self, editor: Editor, pos: int, length: int) -> None:
        self._editor, self._pos, self._length = editor, pos, length
        self._removed = ""                      # undo state, captured by execute()

    def execute(self) -> None:
        self._removed = self._editor.delete(self._pos, self._length)

    def undo(self) -> None:
        self._editor.insert(self._pos, self._removed)


class Revert(Command):
    """Jump back to a checkpoint. Its own undo state is a Memento, as GoF suggests."""

    def __init__(self, editor: Editor, checkpoint: Memento) -> None:
        self._editor, self._checkpoint = editor, checkpoint
        self._before: Memento | None = None

    def execute(self) -> None:
        self._before = self._editor.save()
        self._editor.restore(self._checkpoint)

    def undo(self) -> None:
        assert self._before is not None, "undo() before execute()"
        self._editor.restore(self._before)


# ── Composite: a command made of commands ────────────────────────────────────

class Macro(Command):
    def __init__(self, *commands: Command) -> None:
        self._commands = commands

    def execute(self) -> None:
        for command in self._commands:
            command.execute()

    def undo(self) -> None:
        for command in reversed(self._commands):    # undo in the opposite order
            command.undo()


# ── Invoker: runs commands and keeps them for undo and redo ──────────────────

class History:
    def __init__(self) -> None:
        self._done: list[Command] = []
        self._undone: list[Command] = []

    def do(self, command: Command) -> None:
        command.execute()
        self._done.append(command)
        self._undone.clear()                    # a new edit drops the redo branch

    def undo(self) -> None:
        if self._done:
            command = self._done.pop()
            command.undo()
            self._undone.append(command)

    def redo(self) -> None:
        if self._undone:
            command = self._undone.pop()
            command.execute()
            self._done.append(command)


# ── Composition root: every command is bound to the editor it will change ────

def run() -> list[str]:
    out: list[str] = []
    editor, history = Editor(), History()

    def show(verb: str, label: str = "") -> None:
        out.append(f"{verb:<5} {label:<34} → {editor.text!r}")

    history.do(Insert(editor, 0, "hello"))
    show("do", "insert 'hello'")
    history.do(Insert(editor, 5, " world"))
    show("do", "insert ' world'")
    checkpoint = editor.save()
    show("save", "checkpoint")
    history.do(Macro(Delete(editor, 0, 5), Insert(editor, 0, "goodbye")))
    show("do", "macro: 'hello' → 'goodbye'")
    history.do(Insert(editor, 13, "!"))
    show("do", "insert '!'")
    history.do(Revert(editor, checkpoint))
    show("do", "revert to checkpoint")
    for _ in range(3):
        history.undo()
        show("undo")
    history.redo()
    show("redo")
    history.do(Insert(editor, 13, "?"))
    show("do", "insert '?' (drops the redo branch)")
    history.redo()
    show("redo", "(nothing to redo)")
    return out


if __name__ == "__main__":
    print("\n".join(run()))
