# Training loop: architecture

UML for both shapes of the toy. Both diagrams contain the same roles. What changes is how
those roles are written down.

## Participants

GoF names each role a class plays in a pattern. This table maps each role to the code that
plays it in each shape.

| Pattern | GoF participant | `classic.py` | `modern.py` |
|---|---|---|---|
| Strategy | Strategy | `LRSchedule` (ABC) | `Schedule` (a `Callable` type alias) |
| | ConcreteStrategy | `ConstantLR`, `StepDecay` | `lambda _: 0.1`, `partial(step_decay, ...)` |
| | Context | `Trainer` (holds `_schedule`) | `fit()` (takes `schedule=`) |
| Template Method | AbstractClass | `Trainer` with `fit()` | `fit()` alone: the skeleton is now a function |
| | primitive operation | `train_step()`, abstract | `step`, an argument of type `Step` |
| | hook | `on_fit_start()`, no-op by default | gone: a fresh `StubModel()` starts at loss 1.0 |
| | ConcreteClass | `StubTrainer` | gone: `StubModel` inherits from nothing |
| Observer | Subject | `Trainer` (`attach`, `_notify`) | `fit()`, which loops over `callbacks=` |
| | Observer | `Callback` (ABC) | `Callback` (a `Callable` type alias) |
| | ConcreteObserver | `PrintLogger`, `History` | `log_to(out)` closure, `lambda ...: losses.append(loss)` |

## Classic: one class per role

Each `namespace` box is one pattern. `Trainer` plays two roles. It is the AbstractClass of
Template Method and also the Subject of Observer, so it sits in one box and points into the other.

```mermaid
classDiagram
    direction LR

    namespace Strategy {
        class LRSchedule {
            <<abstract>>
            +lr(epoch: int) float*
        }
        class ConstantLR {
            -_lr: float
            +lr(epoch: int) float
        }
        class StepDecay {
            -_base: float
            -_every: int
            -_gamma: float
            +lr(epoch: int) float
        }
    }

    namespace TemplateMethod {
        class Trainer {
            <<abstract>>
            -_schedule: LRSchedule
            -_callbacks: list~Callback~
            +attach(callback: Callback) None
            +fit(epochs: int) None
            +train_step(lr: float) float*
            +on_fit_start() None
            -_notify(epoch, lr, loss) None
        }
        class StubTrainer {
            +loss: float
            +on_fit_start() None
            +train_step(lr: float) float
        }
    }

    namespace Observer {
        class Callback {
            <<abstract>>
            +update(epoch: int, lr: float, loss: float) None*
        }
        class PrintLogger {
            -_out: list~str~
            +update(epoch, lr, loss) None
        }
        class History {
            +losses: list~float~
            +update(epoch, lr, loss) None
        }
    }

    LRSchedule <|-- ConstantLR
    LRSchedule <|-- StepDecay
    Trainer <|-- StubTrainer
    Callback <|-- PrintLogger
    Callback <|-- History

    Trainer o-- "1" LRSchedule : schedule
    Trainer o-- "*" Callback : notifies
```

There are three inheritance trees and eight classes. Every arrow is nominal: a class takes
part only if it names its base class.

## Modern: one type per role, functions fill it

`Callable[[int], float]` amounts to an interface with a single `__call__` method, so the
diagram draws it that way. Inheritance (`<|--`) becomes structural conformance (`..|>`): a
function satisfies the type just by having a matching signature, without naming anything.

```mermaid
classDiagram
    direction LR

    class Schedule {
        <<type alias>>
        +__call__(epoch: int) float
    }
    class Step {
        <<type alias>>
        +__call__(lr: float) float
    }
    class Callback {
        <<type alias>>
        +__call__(epoch: int, lr: float, loss: float) None
    }

    class fit {
        <<function>>
        +fit(step, *, epochs, schedule, callbacks) None
    }
    class step_decay {
        <<function>>
        +step_decay(epoch, *, base, every, gamma) float
    }
    class log_to {
        <<function>>
        +log_to(out: list~str~) Callback
    }
    class StubModel {
        <<dataclass>>
        +loss: float
        +step(lr: float) float
    }

    fit ..> Schedule : calls
    fit ..> Step : calls
    fit ..> "*" Callback : calls each

    step_decay ..|> Schedule : once partial() binds its params
    StubModel ..|> Step : its bound method .step
    log_to ..> Callback : returns a closure

    note for Schedule "lambda _: 0.1 also fits: a strategy needs no name"
    note for Callback "lambda epoch, lr, loss: losses.append(loss) also fits"
```

All five subclasses are gone. Four were single-method classes that became functions.
`StubTrainer` existed only to supply `train_step()`, and that is now the `step` argument. The
three ABCs became type aliases, which a type checker reads and which do nothing at runtime.

## Runtime: the same loop in both

`fit()` makes the same calls in the same order in both files, which is why `compare.py` can
require identical transcripts.

```mermaid
sequenceDiagram
    participant R as run()
    participant F as fit()
    participant S as schedule
    participant M as model step
    participant C as callbacks

    R->>F: fit(epochs=4)
    Note over F: classic only: on_fit_start() hook
    loop each epoch
        F->>S: classic: schedule.lr(epoch) / modern: schedule(epoch)
        S-->>F: lr
        F->>M: classic: self.train_step(lr) / modern: step(lr)
        M-->>F: loss
        loop each callback
            F->>C: classic: cb.update(epoch, lr, loss) / modern: cb(epoch, lr, loss)
        end
    end
```
