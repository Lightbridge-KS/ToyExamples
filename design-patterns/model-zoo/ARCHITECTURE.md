# Model zoo: architecture

UML for both shapes of the toy. Creational patterns are about *who knows which concrete class
to construct*. In the classic shape that knowledge is spread across a builder, a family
hierarchy, an if/elif chooser and a global. In the modern shape it collapses into a frozen
config, a dict, and an argument.

The products (`Model`, `Preprocessor`) are the same plain dataclasses in both files, because
these patterns are about creating them, not about what they are.

## Participants

| Pattern | GoF participant | `classic.py` | `modern.py` |
|---|---|---|---|
| Builder | Builder / ConcreteBuilder | `ConfigBuilder` | the `ModelConfig` constructor: keyword arguments with defaults |
| | Product | `ModelConfig` (mutable) | `ModelConfig` (frozen; `__post_init__` validates) |
| | Director | `PRESETS` definitions, which chain the setters | none needed |
| Prototype | Prototype | `ModelConfig.clone()` | `dataclasses.replace()` |
| | prototype manager | `PRESETS` dict | `PRESETS` dict |
| Abstract Factory | AbstractFactory | `ModelFamily` (ABC) | `Family`, a `Callable` type alias |
| | ConcreteFactory | `UNetFamily`, `ViTFamily` | `unet()`, `vit()` |
| | AbstractProduct / Product | `Model`, `Preprocessor` | `Model`, `Preprocessor`, returned together in `Bundle` |
| Factory Method | Creator | `ModelFamily.load()` calls the abstract `create_*()` | `create_model()` looks up `_REGISTRY` |
| | ConcreteCreator | the overrides in `UNetFamily` / `ViTFamily` | the functions added by `@register("...")` |
| | (choosing a creator) | `family_for()`: if/elif, edited per new arch | `_REGISTRY[config.arch]`: filled by decorators |
| Singleton | Singleton | `Settings.instance()` with `_instance` | `get_settings()` with `@cache`, or the `settings=` argument |

## Classic: a class for each decision

```mermaid
classDiagram
    direction LR

    namespace BuilderAndPrototype {
        class ConfigBuilder {
            -_arch: str
            -_depth: int
            -_width: int
            -_dropout: float
            +depth(n) ConfigBuilder
            +width(n) ConfigBuilder
            +dropout(p) ConfigBuilder
            +build() ModelConfig
        }
        class ModelConfig {
            +arch: str
            +depth: int
            +width: int
            +dropout: float
            +clone() ModelConfig
        }
    }

    namespace AbstractFactoryAndFactoryMethod {
        class ModelFamily {
            <<abstract>>
            +create_model(config) Model*
            +create_preprocessor() Preprocessor*
            +load(config) tuple
        }
        class UNetFamily {
            +create_model(config) Model
            +create_preprocessor() Preprocessor
        }
        class ViTFamily {
            +create_model(config) Model
            +create_preprocessor() Preprocessor
        }
        class family_for {
            <<function>>
            +family_for(arch) ModelFamily
        }
    }

    namespace SingletonPattern {
        class Settings {
            -_instance: Settings$
            +device: str
            +instance() Settings$
        }
    }

    class Model {
        <<dataclass>>
        +arch: str
        +config: ModelConfig
        +device: str
    }
    class Preprocessor {
        <<dataclass>>
        +steps: tuple~str~
    }

    ConfigBuilder ..> ModelConfig : builds
    ModelFamily <|-- UNetFamily
    ModelFamily <|-- ViTFamily
    family_for ..> UNetFamily : if arch == unet
    family_for ..> ViTFamily : if arch == vit
    UNetFamily ..> Model : creates
    UNetFamily ..> Preprocessor : creates
    ViTFamily ..> Model : creates
    ViTFamily ..> Preprocessor : creates
    UNetFamily ..> Settings : instance()
    ViTFamily ..> Settings : instance()
```

There are two arrows to watch. `family_for` points at *every* concrete family, so adding an
architecture means editing it. Every family points at `Settings` through a static call that
appears in no signature.

## Modern: a registry, a frozen config, and an argument

```mermaid
classDiagram
    direction LR

    class ModelConfig {
        <<frozen dataclass>>
        +arch: str
        +depth: int = 4
        +width: int = 64
        +dropout: float = 0.0
        +__post_init__() None
    }
    class Family {
        <<type alias>>
        +__call__(config: ModelConfig, settings: Settings) Bundle
    }
    class register {
        <<decorator>>
        +register(arch: str) Callable
    }
    class _REGISTRY {
        <<dict>>
        str to Family
    }
    class unet {
        <<function>>
        +unet(config, settings) Bundle
    }
    class vit {
        <<function>>
        +vit(config, settings) Bundle
    }
    class create_model {
        <<function>>
        +create_model(config, *, settings=None) Bundle
    }
    class Bundle {
        <<frozen dataclass>>
        +model: Model
        +preprocessor: Preprocessor
    }
    class Settings {
        <<frozen dataclass>>
        +device: str = cpu
    }
    class get_settings {
        <<cached function>>
        +get_settings() Settings
    }

    unet ..|> Family
    vit ..|> Family
    register ..> _REGISTRY : adds to
    _REGISTRY o-- "*" Family
    create_model ..> _REGISTRY : looks up config.arch
    create_model ..> get_settings : default only
    create_model ..> ModelConfig
    Family ..> Bundle : returns
    Family ..> Settings : receives

    note for ModelConfig "replace(preset, dropout=0.2) is the Prototype"
```

No arrow points at a specific architecture. `create_model` knows only the registry, and
`Settings` arrives as an argument, with `get_settings()` used only as the default.

## Runtime: creating `unet-small` on cuda

The classic shape has to change a global and then restore it:

```mermaid
sequenceDiagram
    participant R as run()
    participant S as Settings
    participant F as family_for
    participant U as UNetFamily

    R->>S: instance().device = cuda
    R->>F: family_for(unet)
    F-->>R: UNetFamily()
    R->>U: load(config)
    U->>U: create_model(config)
    U->>S: instance().device
    U->>U: create_preprocessor()
    U-->>R: (Model, Preprocessor)
    R->>S: finally: instance().device = cpu
```

The modern shape passes settings in and leaves everything else untouched:

```mermaid
sequenceDiagram
    participant R as run()
    participant C as create_model
    participant G as _REGISTRY
    participant U as unet()

    R->>C: create_model(config, settings=Settings(cuda))
    C->>G: _REGISTRY[unet]
    G-->>C: unet
    C->>U: unet(config, settings)
    U-->>R: Bundle(model, preprocessor)
```
