# Model zoo: Factory Method, Abstract Factory, Builder, Prototype, Singleton (toy example)

*Configured models, created by name from presets with their matching preprocessing, plus
shared settings. These are all five GoF creational patterns. The same scenario is written twice: as the GoF book draws it
(101 lines of code, 8 classes) and in modern Python (79 lines, 5 frozen dataclasses). The two
files produce the same transcript.*

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

The creational patterns exist because, in C++ and early Java, constructors are rigid:
1. There are no keyword arguments or defaults.
2. A constructor can't be passed around as a value, and can't be looked up by name.
3. Nothing is immutable by default.

Python removed each of those limits, and the matching pattern shrank into a language
feature:

```
CLASSIC                                         MODERN
───────                                         ──────
ConfigBuilder("unet").depth(3).width(32)        ModelConfig("unet", depth=3, width=32)
    .build()         # validates here               # __post_init__ validates

PRESETS[...].clone(); c.dropout = 0.2           replace(PRESETS[...], dropout=0.2)

class UNetFamily(ModelFamily):                  @register("unet")
    create_model(), create_preprocessor()       def unet(config, settings) -> Bundle: ...
def family_for(arch): if/elif/raise             _REGISTRY[config.arch](config, settings)

Settings.instance().device                      get_settings()            # @cache
                                                create_model(..., settings=Settings("cuda"))
```

These patterns map onto real libraries. `timm` registers architectures with
`@register_model` and builds them with `create_model(name, **overrides)`. Hugging Face's
`AutoModel` and `AutoProcessor` load a matched pair from one name. FastAPI's docs
serve settings from a cached `get_settings()` dependency, which tests can override.

## Classic → modern

| Pattern | Classic (`classic.py`) | Modern (`modern.py`) | What does the work instead |
|---|---|---|---|
| **Builder** | `ConfigBuilder`: one setter per field returning `self`, `build()` validates | `ModelConfig(arch, depth=..., ...)`: defaults + `__post_init__` | keyword arguments, dataclasses |
| **Prototype** | `ModelConfig.clone()` via `copy.copy`, then mutate the copy | `dataclasses.replace(preset, dropout=0.2)` | immutability + `replace()` |
| **Abstract Factory** | `ModelFamily` ABC, one subclass per architecture, two products each | one function per architecture returning a `Bundle(model, preprocessor)` | a function returning a record |
| **Factory Method** | subclasses override `create_*()`; `load()` calls them; `family_for()` picks with if/elif | `@register("unet")` puts the function in `_REGISTRY` | first-class functions + a dict |
| **Singleton** | `Settings.instance()` with a class-level `_instance` | `@cache def get_settings()`, overridable per call with `settings=` | `functools.cache` + dependency injection |

## Why it works

- **Validation can't be skipped.** `replace()` builds a new object, so `__post_init__` runs
  again: `replace(preset, dropout=1.5)` raises. The classic `clone()` followed by
  `c.dropout = 1.5` is accepted silently, because the builder's check ran only once, long
  before the change (verified; exercise 2).
- **Presets can be shared safely.** Frozen presets can't be edited by mistake, so "clone
  before you touch it" stops being a rule people have to remember.
- **A new architecture is one decorated function.** Nothing central is edited. In
  `classic.py` the same change needs a new family class plus an edit to `family_for()`, and
  the error message's list of known names is hard-coded and has to be kept in sync by hand.
- **The dependency is visible.** `create_model(..., settings=...)` shows in its signature
  that it needs settings. Classic `UNetFamily.create_model()` reaches for
  `Settings.instance()` without saying so, and the only way to run it "on cuda" is to change
  the global and restore it in a `finally`.

## The price

- **The registry fills up when modules are imported.** `create_model(ModelConfig("vit"))`
  works only if the module that runs `@register("vit")` has been imported. `timm` imports all
  its model modules up front to avoid this. Plugins from other packages need entry points:
  see [MarkItDown](../../oss-miniature/markitdown/README.md).
- **String keys fail only when the code runs.** The type checker can't see a typo in
  `"vti"`. `family_for()` has the same problem, so it's a trade-off, not a regression.
- **`@cache` is still global state.** Tests that change settings must call
  `get_settings.cache_clear()`, or pass `settings=` explicitly. Dependency injection only
  helps when callers actually use it.
- **`replace()` copies shallowly.** A list field would be shared between the preset and its
  copy (verified). It is safe here only because every field is immutable, which is also why
  the dataclass is frozen.

## When the classic still wins

- **A builder for genuinely step-by-step construction.** Query builders
  (`select(...).where(...).order_by(...)`, Polars' lazy frames) build a value over many calls,
  often in different places. Keyword arguments can't do that. Modern builders of this kind
  are usually immutable: each step returns a new object.
- **A factory method in a framework you subclass anyway.** `logging.Logger.makeRecord` is
  documented as "a factory method which can be overridden in subclasses". The same module
  also offers `logging.setLogRecordFactory(fn)`, the function shape, alongside it.
- **Families with many members.** When a "family" means a connection, a cursor, type
  adapters and an exception hierarchy, a *module* acts as the factory. Every DB-API driver
  provides `connect()`, `Error` and friends at module level.
- **Identity-based singletons.** `None`, sentinels such as `dataclasses.MISSING`, and enum
  members exist exactly once *on purpose*, because code compares them with `is`.

## Variants worth naming

- **GoF's original Builder** has a *Director* that runs a fixed sequence of builder calls,
  so the same steps can produce different representations (an RTF reader building ASCII
  or TeX output). In Python, the Director is a function that takes the builder as a
  parameter.
- **`classmethod` constructors.** `dict.fromkeys`, `int.from_bytes`,
  `datetime.fromtimestamp`, and Hugging Face's `from_pretrained`: Factory Method as an
  alternative constructor on the class itself.
- **Multiton.** `logging.getLogger(name)` returns the same logger for the same name
  (verified). It is a registry of named singletons.

## Where you meet it

- `timm.create_model("resnet50", drop_rate=0.2)` and `@register_model`: Factory Method as a
  registry, with Builder as keyword overrides.
- Hugging Face `AutoModel.from_pretrained(name)` + `AutoProcessor.from_pretrained(name)`:
  Abstract Factory by convention. Both lookups use the same name, so the pair matches.
- Hydra / OmegaConf config overrides: Prototype as "base config + changes".
- FastAPI `Depends(get_settings)` with `app.dependency_overrides` in tests: the cached-getter
  Singleton, injected.

## Exercises

1. **Add `resnet`** to both files. Count the classes, functions and *existing* lines you had
   to touch in each.
2. **Bypass validation.** In `classic.py`, clone a preset and set `dropout = 1.5`. Does
   anything complain? Try the same with `replace()` in `modern.py`. Then make the classic
   shape safe without making `ModelConfig` immutable.
3. **Leak a singleton.** In `classic.py`, remove the `finally` and raise an exception inside
   the `try`. What device does the next line of output report? Write a test that would catch
   it, and the modern equivalent that can't have this bug.
4. **Grow the family.** Add a third product, `postprocess` (sigmoid for UNet, softmax for
   ViT), to both files. GoF list this as Abstract Factory's weak spot. Did the modern shape
   make it any easier?
