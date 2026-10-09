# ToyExamples

A collection of architecture and codebase patterns, each explained through the smallest code example that still shows the mechanism.

## Principles

- **One pattern, one toy.** Each example is minimal and self-contained, and runnable on its own.
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

### OSS Miniature

How the core architecture skeleton of OSS application and libraries were build, demonstrate using miniature toy. 

- [MarkItDown](oss-miniature/markitdown/README.md) (any file to Markdown through one priority-ordered converter registry, with entry-point plugins)
