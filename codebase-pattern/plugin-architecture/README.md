# Plug-in architecture, manifest-first (toy example)

*A radiology report workbench whose plugins are folders: a `plugin.toml` that the host reads
at startup, and Python that the host imports only when a contribution is first used. The
host is about 230 lines of stdlib Python (docstrings included); a notebook comes with it. It is the mirror of
[MarkItDown in miniature](../../oss-miniature/markitdown/README.md), whose host must import a
plugin to learn what it adds.*

```sh
# from this folder (Python 3.11+, for tomllib)
uv run demo.py                                                    # 6 scenes, with an [activate] trace
uv run --with jupyterlab jupyter lab plugin_architecture.ipynb    # one stage per section, plus a live seam test
```

```
plugin-architecture/
├── host.py                       extension points · the gate · discover() · Registry (lazy activation, check())
├── demo.py                       6 scenes
├── plugin_architecture.ipynb     each stage on its own; ends by adding a plugin without touching host.py
├── plugins/                      healthy
│   ├── measure/                  plugin.toml + measure.py        command: "12 mm" → "1.2 cm"
│   ├── report-tools/             plugin.toml + report_tools.py   command: word count
│   └── ct-brain-template/        plugin.toml only                template: data, no code at all
└── plugins-broken/               one failure each
    ├── too-new/                  api = 2; too_new.py raises if imported
    ├── mri-knee-template/        a template with no title
    ├── measure-fork/             claims "measure.to-cm" too; measure_fork.py raises if imported
    └── impression-tools/         the manifest names uppercase(); the code renamed it shout()
```

## The idea

A plugin has two halves. The **manifest** is data: who the plugin is, which host contract it
was built for, and everything it contributes. The **code** is an implementation behind that
data. The host reads all the manifests at startup and builds its whole picture of the
system from them. It imports a plugin's code only when someone uses one of its
contributions, and it imports each module once.

```
 STARTUP: data only                             FIRST USE: code
 ──────────────────                             ───────────────
 plugins/*/plugin.toml                          run("measure.to-cm", text)
        │ tomllib                                       │
        ▼                                               ▼
 parse_manifest ──✗──► rejected                 Command(handler="measure:to_cm"), owner measure
        │ ✓            (schema, api version)            │ not in sys.modules yet?
        ▼                                               ▼
 one owner per contribution id? ──✗──► rejected  import measure/measure.py   ← only now, once
        │ ✓                                             │
        ▼                                               ▼
 Registry: one table per extension point        getattr(module, "to_cm")(text)
   commands:  id · title · owner · handler        ✗ missing → ActivationError (this command only)
   templates: id · title · body
        │
        ▼
 palette · render · check       (no plugin code imported until here)
```

## One decision, pushed to its pole

Seen as one of the nine decisions every plugin mechanism makes, this toy changes only one:
the **manifest split**, the part of a plugin that the host can know *without running plugin
code*. Both toys are the same archetype, **Registered**: in-process, with the host reading
only a registry. They differ on this one decision.

```
                     manifest split
   nothing ──── distribution metadata ─────────── full declared surface
                        ▲                                   ▲
                    markitdown                         this toy
                 import, then learn                learn, then maybe import
```

| | MarkItDown in miniature | This toy |
|---|---|---|
| What the host reads first | an entry point: a name pointing at `register_converters()` | `plugin.toml`: identity, api version, every contribution |
| To list everything plugins add | import every plugin and run its registration | parse files; import nothing |
| Compatibility is checked | at install, by the plugin's version range on `minimd` | at discovery, by the `api` field, before any code is read |
| Two plugins claim the same thing | ordered by priority; both stay | found from data and rejected, before any code runs |
| Where the truth lives | one place: the code | two places: the manifest and the code (they can drift) |

## Six ideas, and where each lives

| # | Idea | In the code |
|---|---|---|
| 1 | **The manifest is the contract.** Identity, host api version, and every contribution are data. A command's code is a string, `"module:function"`, which the host follows later. | `plugin.toml`, `parse_manifest()` |
| 2 | **The host owns the extension points.** A plugin fills slots, and each slot's dataclass fields are the keys a manifest must give. A new plugin needs no host change. A new kind of slot does. | `EXTENSION_POINTS`, `Command`, `Template` |
| 3 | **Discovery reads data and never runs code.** The palette, the owners, and the conflicts all come from parsed TOML. | `discover()`, `Registry.palette()` |
| 4 | **Activation is lazy, follows from use, and happens once.** Declaring a command means "import me when it runs". `sys.modules` is the cache. | `Registry._activate()` |
| 5 | **The gate runs before code.** Schema, api version, and whole-system conflicts reject a plugin while its code is still unread. | `ManifestError`, the claims loop in `discover()` |
| 6 | **Drift is the price; a contract test is the remedy.** Data cannot know that the code renamed a function. Use finds it; `check()` finds it earlier. | `ActivationError`, `Registry.check()` |

## Six scenes the demo shows

1. **The palette, with no plugin code imported.** Two commands and a template, with titles
   and owners, from three TOML files. `sys.modules` holds no plugin module.
2. **Lazy activation.** The first `measure.to-cm` run prints `[activate] measure`, and
   `measure.py`'s top-level line runs: importing a plugin executes its code. The second run
   reuses the module. `report_tools.py` is still untouched.
3. **A data-only plugin.** `ct-brain-template` has no Python file. The host renders its body.
4. **The gate runs before code.** `too-new` (api 2) and `mri-knee-template` (no title) are
   rejected, each with a reason and a field path. `too_new.py` raises on import, and the demo
   keeps running, so the file was never read.
5. **Conflicts are found from data.** `measure` and `measure-fork` both claim
   `measure.to-cm`, and both are rejected. A healthy plugin goes down with the bad one; in
   exchange, no winner is picked by folder order.
6. **Manifest drift.** `impression.extract` works. `impression.uppercase` fails with
   `ActivationError`, only for that command. `check()` reports the same drift without anyone
   running the command, and imports every code plugin to do it.

## The nine decisions

| # | Decision | This toy |
|---|---|---|
| 1 | Contract | A data schema for each extension point, plus a plain `(str) -> str` handler. The template plugin is a **bundle**: a manifest over data, with no code contract. |
| 2 | Manifest split | **The full declared surface**, which is the point of the toy. |
| 3 | Placement | The same process as the host. |
| 4 | Activation | Lazy: on first use of a contribution, once. |
| 5 | Change landing | Restart: `discover()` runs once, at startup. |
| 6 | Compatibility | An integer `api` gate, checked before code. Handlers import nothing from the host, so no SDK can break under them. |
| 7 | Core/plugin line | The host keeps validation, conflict policy, activation, and the error types. It never branches on a plugin id. |
| 8 | Distribution | Copy a folder into `plugins/`. |
| 9 | Enforcement | The schema and api gate at discovery; the `check()` contract test, for CI. |

## Why a plugin seam here, and not something lighter

Each concern should get the least powerful mechanism that does the job.

| Concern | Who changes it | Mechanism it needs |
|---|---|---|
| Report commands (unit conversion, word count) | other developers, with code | a plugin with a handler: the reason this seam exists |
| Report templates | any radiologist, with text | data only; it rides in a plugin folder as a bundle, with no handler |
| The host contract (`API_VERSION`, the extension points) | the host's author | the fixed core: only a host release changes it |

If every contribution were a template, a folder of TOML files that the host reads would be
enough. The handler machinery pays for itself only because some contributions are code.

## What a manifest does not do

- **It does not isolate.** Plugin code runs in the host's process. A lazy import delays the
  code; it does not contain it. Scene 2 shows a module's top-level code running on import.
  A plugin that loops forever freezes the host.
- **It does not enforce.** A manifest says what a plugin *claims* to add, and you can review
  that before you run anything. Once imported, the code can do anything the host can.
- **What it controls is admission.** Plugin code runs only if three things are true:
  someone wrote a folder into `plugins/`, the manifest passed the gate, and the host was
  restarted. An AI agent with file tools can write a plugin folder. Because discovery runs
  only at startup and the gate runs before any code, the new plugin does nothing until the
  next start, and the gate has checked it by then.
- **Isolation needs a process wall.** VS Code runs extensions in a separate process, so a
  hung extension cannot freeze the editor. That is the **Hosted** archetype, and it makes
  every call across the wall asynchronous.

## The price

- **Two sources of truth.** The manifest and the code can disagree, and the data cannot
  know (scene 6). The disagreement shows up on first use, or in a `check()` run.
- **The handler is a string.** No type checker follows `"impression_tools:uppercase"`, and
  no editor jumps to it. The `(str) -> str` signature is a promise in the docs; `host.py`
  has to `cast()` it.
- **The schema is a frozen public API.** Every key in `plugin.toml` is a promise to every
  plugin author. Changing one means a new `api` number.
- **Contributions must be known in advance.** A plugin that computes its commands at
  runtime (one per file in a folder, say) does not fit a static manifest.
- **The conflict policy has a victim.** Rejecting both claimants means a healthy plugin goes
  down with a bad one (scene 5). First-wins keeps it, but then a folder name picks the
  winner.

## Where you meet it

- **napari's npe2** is the closest match. Each plugin ships a `napari.yaml` whose
  contributions (commands, readers, writers, widgets) point at `python_name:
  package.module:function`. napari builds menus and picks readers from the manifests, and
  imports a plugin when a contribution is used. npe2 replaced napari's earlier hook-based
  plugin engine, which was code-first.
- **VS Code** has the same manifest split, with `contributes` and `activationEvents` in
  `package.json`. Contributed commands imply their own activation event. It adds the process
  wall: the extension host.
- **Eclipse**, where the term "extension point" comes from. `plugin.xml` declares extension
  points and the extensions that fill them, and bundles activate lazily.
- **Claude Code skills.** A skill's frontmatter (`name`, `description`) is read at startup;
  the body is read only when the skill is used. It is the same split, applied to a model's
  context instead of a process's imports.
- **Obsidian**, as a counterpoint. Its `manifest.json` has a version gate (`minAppVersion`)
  but no contributions. Plugins register their commands in code when they load, which is
  MarkItDown's end of the spectrum.

## What the toy leaves out

How a host finds manifests in installed packages (npe2 uses an entry point that points at the
manifest file; MarkItDown in miniature already shows entry points); dependencies between
plugins; permissions or capability declarations; an enable/disable list; activation events
other than "first use"; reloading plugins while the host runs; semantic version ranges for
`api`. None of them change the shape.

## Exercises

1. Add a `plugins/measure-inch/` folder with a `measure.to-inch` command. What did you change
   in `host.py`? (Nothing. The notebook's last section does this live.)
2. Add an extension point `checks`: a handler that returns warnings for a report. What did
   you change in `host.py` this time, and why is that by design?
3. Make discovery eager: have `discover()` call `check()` on the registry before it returns
   it. Which scenes change?
   What did you gain (look at scene 6), and what does every startup now pay?
4. Change the conflict policy to first-wins. Which plugin owns `measure.to-cm` in scene 5,
   and what decided it?
5. Put `while True: pass` at the top of `report_tools.py`. Which scene hangs, and why not
   scene 1? What would a Hosted host have done?
6. Rename `measure.py` to `convert.py` and leave the manifest alone. Which of these notices:
   `discover()`, `check()`, `uvx pyright host.py demo.py`? Why can't the type checker?
