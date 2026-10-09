# Undo/redo: architecture

UML for both shapes of the toy. The biggest change is where the knowledge lives. In the
classic shape, each command knows its receiver and its own inverse. In the modern shape,
commands know nothing, one function knows what they mean, and the history holds values
instead of actions.

## Participants

| Pattern | GoF participant | `classic.py` | `modern.py` |
|---|---|---|---|
| Command | Command | `Command` ABC: `execute()`, `undo()` | `Command`: a union of four frozen dataclasses |
| | ConcreteCommand | `Insert`, `Delete`, `Revert`, each holding the `Editor` | `Insert`, `Delete`, `Revert`: fields only |
| | Receiver | `Editor`: `insert()`, `delete()` | `apply(text, command)`: the receiver's logic as one function |
| | Invoker | `History`: `_done` / `_undone` stacks of commands | `History`: `past` / `present` / `future` values |
| | Client | `run()` binds each command to the editor | `run()` builds commands as plain values |
| Memento | Memento | `Memento`, with an opaque `_state` | the previous `str` |
| | Originator | `Editor`: `save()`, `restore()` | none: no object owns mutable state |
| | Caretaker | `run()` (holds `checkpoint`), `Revert` (holds `_before`) | `History.past`, the `checkpoint` variable |
| Composite | Component | `Command` | `Command` |
| | Leaf | `Insert`, `Delete`, `Revert` | `Insert`, `Delete`, `Revert` |
| | Composite | `Macro`: forwards `execute()`, reverses `undo()` | `Macro`, unfolded by `reduce(apply, steps, text)` |

## Classic: commands that carry their receiver and their inverse

```mermaid
classDiagram
    direction LR

    namespace CommandPattern {
        class Command {
            <<abstract>>
            +execute() None*
            +undo() None*
        }
        class Insert {
            -_editor: Editor
            -_pos: int
            -_text: str
            +execute() None
            +undo() None
        }
        class Delete {
            -_editor: Editor
            -_pos: int
            -_length: int
            -_removed: str
            +execute() None
            +undo() None
        }
        class Revert {
            -_editor: Editor
            -_checkpoint: Memento
            -_before: Memento
            +execute() None
            +undo() None
        }
        class History {
            -_done: list~Command~
            -_undone: list~Command~
            +do(command: Command) None
            +undo() None
            +redo() None
        }
    }

    namespace MementoPattern {
        class Editor {
            +text: str
            +insert(pos, s) None
            +delete(pos, length) str
            +save() Memento
            +restore(memento: Memento) None
        }
        class Memento {
            -_state: str
        }
    }

    namespace CompositePattern {
        class Macro {
            -_commands: tuple~Command~
            +execute() None
            +undo() None
        }
    }

    Command <|-- Insert
    Command <|-- Delete
    Command <|-- Revert
    Command <|-- Macro
    Macro o-- "*" Command : children
    History o-- "*" Command : done / undone
    Insert --> Editor : receiver
    Delete --> Editor : receiver
    Revert --> Editor : receiver
    Revert --> Memento : undo state
    Editor ..> Memento : creates
```

Every concrete command points at `Editor`. That arrow is the coupling that makes a classic
command hard to log, send, or replay elsewhere: it isn't a description of an edit, it is an
edit already wired to one object.

## Modern: commands as data, history as values

```mermaid
classDiagram
    direction LR

    class Command {
        <<type alias>>
        Insert | Delete | Revert | Macro
    }
    class Insert {
        <<frozen dataclass>>
        +pos: int
        +text: str
    }
    class Delete {
        <<frozen dataclass>>
        +pos: int
        +length: int
    }
    class Revert {
        <<frozen dataclass>>
        +to: str
    }
    class Macro {
        <<frozen dataclass>>
        +steps: tuple~Command~
    }
    class apply {
        <<function>>
        +apply(text: str, command: Command) str
    }
    class History {
        <<frozen dataclass>>
        +present: str
        +past: tuple~str~
        +future: tuple~str~
        +do(command: Command) History
        +undo() History
        +redo() History
    }

    Insert ..|> Command
    Delete ..|> Command
    Revert ..|> Command
    Macro ..|> Command
    Macro o-- "*" Command : steps
    apply ..> Command : matches on
    History ..> apply : do() calls

    note for History "undo and redo never touch a command"
```

The arrows to `Editor` are gone, because there is no editor. Only `apply` depends on the
command types. `History` uses `apply` once, in `do()`, and never again.

## Runtime: undoing the macro

Classic undo is a recursive walk that runs every inverse operation in reverse order:

```mermaid
sequenceDiagram
    participant R as run()
    participant H as History
    participant M as Macro
    participant I as Insert
    participant D as Delete
    participant E as Editor

    R->>H: undo()
    H->>M: undo()
    M->>I: undo()
    I->>E: delete(0, 7)
    M->>D: undo()
    D->>E: insert(0, _removed)
    Note over H: the macro moves to _undone, ready for redo
```

Modern undo makes no call into any command:

```mermaid
sequenceDiagram
    participant R as run()
    participant H as History

    R->>H: undo()
    H-->>R: History(past[-1], past[:-1], (present, *future))
    Note over H: no command runs, a stored value moves back into present
```
