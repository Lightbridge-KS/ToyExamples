# Ports & Adapters (toy example)

*Completing a to-do task, with two kinds of storage and two notifiers plugged into one core, in ~140 lines of stdlib Python, plus a notebook.*

```sh
# from this folder
uv run ports_adapters_toy.py                                  # scripted: both wirings
uv run --with jupyterlab jupyter lab ports_adapters.ipynb     # interactive walkthrough
```

## The idea

Split the code into a **core**, which holds the business rules and knows no technology, and
**adapters**, which plug a technology into the core. They meet at **ports**: interfaces
that the *core* defines in its own terms. Adapters depend on ports. The core depends on
nothing outside itself.

```
     DRIVING side                                          DRIVEN side
     (calls the core)                                      (the core calls out)

                     ┌─────────────────────────────────┐
   cli()  ─────┐     │              CORE               │      ┌──── InMemoryTaskRepository
               ├────►○ execute()       ITaskRepository ○◄─────┤
   a test ─────┘     │                                 │      └──── JsonFileTaskRepository
                     │  CompleteTask                   │
                     │  Task (entity + its rule)       │      ┌──── ConsoleNotifier
                     │                       INotifier ○◄─────┤
                     │                                 │      └──── SpyNotifier
                     └─────────────────────────────────┘

   ○ = a port, owned by the core.  Every arrow means "depends on", and all of them point inward.
```

Both sets of arrows point **inward**. The core never imports an adapter. It only names the
ports it owns, and **the composition root** (`demo_*()`) is the one place that chooses which
adapter fills which port.

## The parts, and where each lives

| Part | Role | In the code |
|---|---|---|
| **Entity** | domain data plus its rules ("can't complete twice") | `Task`, `Task.complete()` |
| **Driving (primary) port** | what the core *offers*: the use case's public method | `CompleteTask.execute()` |
| **Driven (secondary) ports** | what the core *needs*, stated in core terms | `ITaskRepository`, `INotifier` |
| **Driving adapter** | turns outside input into a call on the driving port | `cli("done 1", ...)` |
| **Driven adapters** | implement a driven port with a technology, translating `Task` to and from it | `InMemoryTaskRepository`, `JsonFileTaskRepository`, `ConsoleNotifier`, `SpyNotifier` |
| **Composition root** | the only code that knows both sides; it wires adapters into ports | `demo_production()`, `demo_test()` |

Two choices in the toy are deliberate:

- **The driving port has no ABC.** There is one use-case implementation, so an
  `ICompleteTask` interface would only pass calls through. The public method *is* the port.
  Driven ports get ABCs because they have several implementations.
- **Ports are named for the core's need, not the technology.** `ITaskRepository`, not
  `IJsonStore`. The core asks for "a place tasks live", and JSON is one answer.

## Two wirings the demo shows

1. **Production wiring.** `cli` → `CompleteTask` → `JsonFileTaskRepository` +
   `ConsoleNotifier`. A real file on disk flips to `"done": true` and a line prints.
2. **Test wiring.** The test calls `execute()` itself, and `InMemoryTaskRepository` +
   `SpyNotifier` replace disk and console. There is no file and no output to parse: the
   test asserts on the spy's `sent` list.

The core's code is **identical** in both. Only the composition root changed. A test is just another driving adapter.

## Why it works

- **Swap technology without touching the rules.** A second adapter for the same port
  (`JsonFile...` next to `InMemory...`) shows that the seam is real, not decorative.
- **Fast, honest tests of the core.** Business logic runs with no disk, network, or clock,
  so a unit test is a function call.
- **The rules can't leak into the edges.** `Task.complete()` raises on a double-complete
  no matter which driver called it or which store holds the task.
- **Translation is fenced in.** `Task(**rows[...])` and `asdict(task)` happen only inside
  the JSON adapter. The core never sees a dict.

## The price

- **Indirection.** Two ABCs, four adapters, and a wiring function for one use case. In a
  CRUD app with no real rules, the core is empty and the hexagon is ceremony.
- **Fakes can lie.** `InMemoryTaskRepository.get()` returns the *live* object, so
  forgetting `save()` still passes the test while production silently loses the write
  (exercise 1). A port is a contract, and every adapter, fakes included, must honor it.
  Contract tests run against each adapter to catch exactly this.
- **Port design is the hard part.** Too narrow and every feature changes the port; too
  wide and you've rebuilt the technology's API inside the core.
- **Wiring grows.** One composition root is fine for a toy. Real apps reach for a
  container or a factory module, which is one more thing to learn.

## Variants worth naming

- **Hexagonal / Onion / Clean Architecture.** These are the same dependency rule
  (point inward) with different numbers of rings. Clean adds explicit use-case and
  interface-adapter layers; Ports & Adapters keeps just *inside* vs *outside*.
- **Port style.** `ABC` (nominal, checked at instantiation) vs `typing.Protocol`
  (structural, checked by a type checker only). Protocol lets an adapter satisfy a port
  without importing it.
- **Use case as class vs function.** `CompleteTask` holds its dependencies, but a
  function `complete_task(task_id, repo, notifier)` is the same port with less ceremony.

## Where you meet it

Alistair Cockburn's original "Hexagonal Architecture" (2005); repository and gateway
layers in DDD codebases; Django/FastAPI projects that keep a `domain/` package free of
ORM imports; any test suite that swaps a real database or email sender for an in-memory
fake; and plugin systems where the host defines an interface and third parties implement it.

## Exercises

1. Delete `self._repo.save(task)` from `CompleteTask.execute()` and run the file. Which
   wiring notices? Then write one check that runs against **both** repositories and fails
   for the in-memory one too.
2. Add a third driven adapter, `SqliteTaskRepository`, using stdlib `sqlite3`. How many
   lines of the core changed? (Zero is the goal.)
3. Add a second driving adapter, `http(request_dict, use_case)`. What does it share with
   `cli`, and what does neither of them know?
4. Move `Task.complete()`'s "already done" check into `cli`. Which wiring loses the rule?
   That is the bug the hexagon exists to prevent.
