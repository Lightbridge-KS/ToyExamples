# Design patterns, modern edition

The 23 "Gang of Four" patterns (Gamma, Helm, Johnson, Vlissides, 1994), as they look in
Python 3.12+.

Most of them haven't disappeared. They have been **absorbed into the language**:

- an interface with one method becomes a function;
- a class hierarchy over a closed set of node types becomes a few frozen dataclasses handled with `match`;
- a hand-written iterator becomes `yield`.

Peter Norvig counted 16 of the 23 as "invisible or simpler" in dynamic languages back in 1996.
Each toy shows that absorption happening, and also the part most tutorials skip: **when the
classic shape still earns its keep.**

## How each toy is laid out

A toy groups the patterns that one language mechanism absorbs together, so the patterns in it
cooperate on one scenario rather than being bolted on.

```
<toy>/
├── README.md        the idea, classic → modern table, price, when the classic still wins, exercises
├── ARCHITECTURE.md  Mermaid UML: GoF participants table, classic and modern class diagrams, runtime sequences
├── classic.py       the scenario, shaped as the GoF book draws it
├── modern.py        the same scenario, in idiomatic Python 3.12+
└── compare.py       proof: both files must print the same transcript
```

`classic.py` and `modern.py` are separate so they can be diffed side by side
(`code --diff classic.py modern.py`). Every file is stdlib-only and runs with `uv run`.

## Toys, in reading order

Each toy reuses the move taught by the toys before it.

| # | Toy | Scenario | Patterns | Absorbed by | Code lines, classic → modern |
|---|---|---|---|---|---|
| 1 | [training-loop](training-loop/README.md) | train a stub model with LR schedules and callbacks | Strategy, Template Method, Observer | first-class functions, `partial`, lists of callables | 70 → 40 |
| 2 | [undo-redo](undo-redo/README.md) | text buffer with undo/redo and macros | Command, Memento, Composite | frozen dataclass commands, an `apply()` reducer, immutable snapshots | 103 → 74 |
| 3 | [middleware](middleware/README.md) | `handle(request)` with auth, logging, cache | Chain of Responsibility, Decorator, Proxy | `@decorator`, `Handler → Handler` stacks, `functools.cache` | 58 → 57 |
| 4 | [expression-tree](expression-tree/README.md) | `((x + 0) * 1) + (2 * 3)`: evaluate, print, simplify, walk | Composite, Interpreter, Visitor, Iterator | frozen dataclasses handled with `match`, generators | 114 → 84 |
| 5 | [model-zoo](model-zoo/README.md) | `create_model("unet", ...)` from presets | Factory Method, Abstract Factory, Builder, Prototype, Singleton | registry + `@register`, keyword args, `replace()`, a cached getter / DI | 101 → 79 |
| 6 | [report-workflow](report-workflow/README.md) | radiology report: draft → preliminary → final → appended | State (+ Strategy twin, Observer hooks) | `StrEnum` + transition table, `match` | 96 → 78 |

Modern is usually shorter, but not always: in `middleware` it saves one line. The gain
worth looking for is in what *kind* of thing each part becomes (a function, a value, a table
row), and in which bugs become impossible. Counts exclude blank lines, comments and docstrings.

## The map: all 23 patterns

"Modern form" is the usual Python shape today. "Goes by" lists the names people search for
now, which often hide the pattern's GoF origin.

### Creational: how objects get made

| Pattern | GoF intent, in short | Modern form | Goes by | Where |
|---|---|---|---|---|
| Abstract Factory | create families of objects that must match | one lookup returns the matched set (a bundle, a module) | `AutoModel` + `AutoProcessor`, DI container | [model-zoo](model-zoo/README.md) |
| Builder | construct a complex object step by step | keyword args + dataclass defaults + `__post_init__`; fluent builder only for stepwise queries | query builders (SQLAlchemy `select()`, Polars lazy) | [model-zoo](model-zoo/README.md) |
| Factory Method | let subclasses choose the class to instantiate | registry dict + `@register` decorator; `classmethod` constructors | plugin registry, `create_model()`, `from_pretrained()` | [model-zoo](model-zoo/README.md); [MarkItDown](../oss-miniature/markitdown/README.md) |
| Prototype | make new objects by copying an existing one | `dataclasses.replace()`, `copy.deepcopy()` | presets, config overrides | [model-zoo](model-zoo/README.md) |
| Singleton | exactly one instance, reachable globally | module-level object; `@cache`'d getter; or just pass it in | DI scope, FastAPI `Depends(get_settings)` | [model-zoo](model-zoo/README.md) |

### Structural: how objects are composed

| Pattern | GoF intent, in short | Modern form | Goes by | Where |
|---|---|---|---|---|
| Adapter | make one interface fit another | wrapper satisfying a `Protocol` | ports & adapters, anti-corruption layer | [Ports & Adapters](../codebase-pattern/ports-adapter/README.md) |
| Bridge | vary an abstraction and its implementation independently | composition: pass the implementation in | backends, drivers, dialects | map only: it is plain composition / DI |
| Composite | treat a part and the whole uniformly | recursive dataclasses; a list of X that is itself an X | trees: ASTs, DOM, component trees | `undo-redo`, [expression-tree](expression-tree/README.md) |
| Decorator | add behaviour by wrapping | `@decorator`; a wrapper with the same interface | middleware, `@retry`, `@lru_cache` | [middleware](middleware/README.md) |
| Facade | one simple entry point to a subsystem | a package's `__init__` public API | public API, SDK client | [Module communication](../codebase-pattern/module-communication/README.md) |
| Flyweight | share many fine-grained instances | `@cache`'d constructor, `sys.intern`, `__slots__` | interning, instance cache | map only: rarely hand-written today |
| Proxy | a stand-in that controls access to an object | `functools.cache`, `cached_property`, `__getattr__` forwarding | lazy loading, caching layer, RPC stub | [middleware](middleware/README.md) |

### Behavioral: how objects share work

| Pattern | GoF intent, in short | Modern form | Goes by | Where |
|---|---|---|---|---|
| Chain of Responsibility | pass a request along handlers until one takes it | middleware stack of `Handler → Handler` | middleware (ASGI, Django, Express) | [middleware](middleware/README.md) |
| Command | a request as an object | frozen dataclass message, or a callable | actions, Redux actions, task queues, event sourcing | [undo-redo](undo-redo/README.md) |
| Interpreter | a grammar as classes; evaluate its sentences | AST as dataclasses + `match` | DSL, rule engine | [expression-tree](expression-tree/README.md) |
| Iterator | walk a collection without exposing its insides | generator, `yield from`, the iterator protocol | lazy streams, `itertools` | [expression-tree](expression-tree/README.md) |
| Mediator | one object coordinates its peers | orchestrator, event bus | orchestration, message broker | [Module communication](../codebase-pattern/module-communication/README.md) |
| Memento | capture and restore state without breaking encapsulation | keep the old immutable value | snapshots, time-travel debugging | [undo-redo](undo-redo/README.md) |
| Observer | notify dependents of a change | a list of callables; signals; pub/sub | callbacks, signals, reactive streams | [training-loop](training-loop/README.md); pub/sub in [Module communication](../codebase-pattern/module-communication/README.md) |
| State | behaviour changes with internal state | `StrEnum` + transition table, `match` | finite-state machine (FSM) | [report-workflow](report-workflow/README.md) |
| Strategy | interchangeable algorithms behind one interface | pass a function | `key=` functions, policies | [training-loop](training-loop/README.md) |
| Template Method | fixed skeleton, subclasses fill the steps | skeleton function that takes its steps as arguments | framework hooks vs callbacks | [training-loop](training-loop/README.md) |
| Visitor | add operations to a class hierarchy without changing it | `match`, `functools.singledispatch` | AST passes, linters, codemods | [expression-tree](expression-tree/README.md) |

Coverage: 18 patterns get toys in this folder. Adapter, Facade and Mediator are already covered by
the [codebase patterns](../codebase-pattern/). Bridge and Flyweight are left as map
entries, because a toy for either would be contrived.
