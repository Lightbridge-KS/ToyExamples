# Undo/redo: Command, Memento, Composite (toy example)

*A text buffer with undo, redo, a checkpoint, and a macro that undoes as one step. The same
scenario is written twice: as the GoF book draws it (103 lines of code, 8 classes) and in
modern Python (74 lines, 5 frozen dataclasses). The two files produce the same transcript.*

```sh
# from this folder
uv run classic.py     # the GoF shape
uv run modern.py      # the modern shape
uv run compare.py     # proof: both transcripts are identical
```

Read the two side by side: `code --diff classic.py modern.py`, or select both in VS Code's
Explorer and choose **Compare Selected**. UML for both shapes is in
[ARCHITECTURE.md](ARCHITECTURE.md).

## The idea

The classic shape makes undo the *command's* job. Each command knows how to reverse itself:
`Delete` remembers the text it removed, and `Revert` keeps a Memento of what it overwrote.

The modern shape makes **state immutable**, and undo stops being anyone's job:

```
CLASSIC                                       MODERN
───────                                       ──────
class Delete(Command):                        @dataclass(frozen=True)
    __init__(editor, pos, length)             class Delete: pos: int; length: int
    execute(): self._removed = editor.delete
    undo():    editor.insert(_removed)        apply(text, Delete(p, n)) -> new text

editor.save() -> Memento(_state)              checkpoint = history.present   # it's a str

History: _done / _undone stacks of commands   History(past, present, future) of values
undo(): command.undo()                        undo(): step back to past[-1]
```

Once old values can't change, a value you kept *is* a snapshot. Memento becomes "keep a
reference", and a Command no longer needs `undo()`, so it shrinks to **data**: a record of
what to do, with no receiver and no methods. One function, `apply(text, command)`, gives that
data its meaning.

## Classic → modern

| Pattern | Classic (`classic.py`) | Modern (`modern.py`) | What does the work instead |
|---|---|---|---|
| **Command** | `Command` ABC with `execute()` and `undo()`; each command holds its `Editor` | frozen dataclasses, plus one `apply(text, command) -> text` with `match` | data + a reducer |
| **Memento** | `Editor.save()` / `restore()`; opaque `Memento._state` | the previous `str`; `History.past` is a tuple of them | immutability |
| **Composite** | `Macro(Command)` runs its children forward and undoes them in reverse | `Macro(steps)` plus `case Macro(steps): reduce(apply, steps, text)` | recursion + `functools.reduce` |

## Why it works

- **A command with no receiver can go anywhere.** A classic `Insert` holds a reference to one
  `Editor`. A modern `Insert(0, "hello")` is plain data, so it can be logged, sent, and
  stored. `asdict()` turns it into a dict, `pickle` round-trips it, and
  `reduce(apply, log, "")` replays a whole log into the final text. That replay is event
  sourcing in one line (verified).
- **No inverse to get wrong.** Classic `Delete.undo()` only works if `execute()` captured the
  removed text first. Modern undo can't be wrong, because it doesn't compute anything.
- **Encapsulation is free.** GoF go to some effort to keep a Memento opaque, so the caretaker
  can hold it without reading or changing it. An immutable value needs no such guard: anyone
  can read it, and nobody can change it.
- **Undo and redo are the same move.** `History.undo()` and `redo()` just move one value
  between `past`, `present` and `future`. This is the shape `redux-undo` uses.

## The price

- **One full copy per step.** Each `History.past` entry here is a whole string. That's fine
  for a toy, but it means storing gigabytes of copies for a large image or document. (See
  *Variants* for structural sharing.)
- **`apply()` is closed.** Every new command type means editing `apply()`. In the classic
  shape a new command is a new class, and nothing else changes. This trade-off is the
  *expression problem*; [expression-tree](../expression-tree/README.md) is built around it.
- **Redo replays a value, not a command.** That's equivalent here because `apply()` is
  pure. If a command read the clock or a database, re-running it could give a different
  result, while the stored value never changes.

## When the classic still wins

- **State too large to copy.** Image editors, video timelines and databases store
  *deltas*, and each delta knows its inverse. ProseMirror's `Step.invert(doc)` is a classic
  undoable Command in a modern library.
- **Effects outside the program.** A command that sent an email or charged a card can't be
  undone by restoring a snapshot. It needs a *compensating* action, the inverse-op idea
  again (sagas, in distributed systems).
- **An open set of commands.** When plugins add new commands, a central `match` can't list
  them. Editors such as VS Code register commands by name instead: an open registry of
  callables, closer to the classic shape than to a closed `match`.

## Variants worth naming

- **Structural sharing.** Persistent data structures (`pyrsistent`, Immutable.js, Clojure's
  vectors) make each version share most of its memory with the one before. That gives you
  modern-shaped undo at a fraction of the cost of full copies.
- **Command log instead of snapshots.** Keep the commands, not the values, and rebuild state
  with `reduce(apply, log, initial)`. Add periodic snapshots so a replay doesn't start from
  zero: this is event sourcing.
- **Commands as closures.** A `(do, undo)` pair of lambdas is the lightest Command. It is
  callable, but it can't be printed, compared or serialized the way dataclass commands can.

## Where you meet it

- Redux / `useReducer` / the Elm architecture: actions are data, a reducer applies them, and
  `redux-undo` keeps `past`, `present`, `future`.
- Event sourcing and write-ahead logs: the log of commands is the source of truth.
- `git`: commits are immutable snapshots with structural sharing, and `revert` adds a new
  commit rather than erasing an old one.
- Task queues (Celery, RQ): a job is a serialized command, run by a worker somewhere else.

## Exercises

1. **Replay.** Keep a log of every command in both files, then rebuild the final text on a
   *fresh* buffer. In `classic.py`, what stops you from re-running the same command objects?
2. **Serialize.** Write the modern log to JSON and read it back. `asdict(Delete(0, 5))` gives
   `{"pos": 0, "length": 5}`, which has no class name. Add a type tag so loading knows which
   class to build.
3. **Add `Upper(pos, length)`**, which uppercases a span, to both files. Which file needed an
   inverse? Which one forced you to edit existing code?
4. **Measure.** Perform 10,000 single-character inserts. Compare the memory held by modern
   `History.past` with classic `History._done`. At what size would you switch shapes?
