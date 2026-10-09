# ToyExamples

A collection of architecture, codebase and design patterns, each explained through the smallest code example that still shows the mechanism.

## Principles

- **One mechanism, one toy.** Each example is minimal and self-contained, and runnable on its own. A toy may show several patterns when one mechanism links them.
- **Mechanism over realism.** The code exists to show why the pattern works, its trade-offs included, not to be production-ready.
- **Explore interactively.** Where useful, an example also comes as a notebook to poke at.

## Patterns

### Architecture patterns

How the parts of a system talk to each other at runtime.

- Hub-and-spoke (a smart-home hub and devices)
- Fleet (agents phoning home to a control plane)

### Codebase patterns

How the code of one program is arranged, and which way its dependencies point.

- Ports & Adapters (one to-do core, swappable storage and notifiers)
- [Module communication](codebase-pattern/module-communication/README.md) (public APIs, checkout orchestration, and a pub/sub event bus)

### Design patterns

The Gang of Four patterns in modern Python: what the language absorbed, and when the classic shape still wins. Each toy has `classic.py` and `modern.py` to diff side by side. See the [map of all 23](design-patterns/README.md).

- [Training loop](design-patterns/training-loop/README.md) (Strategy, Template Method, Observer → functions, `partial`, callbacks)
- [Undo/redo](design-patterns/undo-redo/README.md) (Command, Memento, Composite → commands as data, immutable snapshots)
- [Middleware](design-patterns/middleware/README.md) (Chain of Responsibility, Decorator, Proxy → `Handler -> Handler` functions)
- [Expression tree](design-patterns/expression-tree/README.md) (Composite, Interpreter, Visitor, Iterator → dataclasses, `match`, generators)
- [Model zoo](design-patterns/model-zoo/README.md) (Factory Method, Abstract Factory, Builder, Prototype, Singleton → registry, keyword args, `replace()`, `@cache`)
- [Report workflow](design-patterns/report-workflow/README.md) (State, Observer → a transition table that draws itself)

### OSS Miniature

How the core architecture skeleton of OSS application and libraries were build, demonstrate using miniature toy. 

- [MarkItDown](oss-miniature/markitdown/README.md) (any file to Markdown through one priority-ordered converter registry, with entry-point plugins)
