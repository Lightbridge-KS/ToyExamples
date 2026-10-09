# Training loop: Strategy, Template Method, Observer (toy example)

*A stub model trained under two learning-rate schedules, with callbacks. The same scenario is
written twice: as the GoF book draws it (70 lines of code, 8 classes) and in modern Python
(40 lines, 1 class). The two files produce the same transcript.*

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

All three patterns share one move. **An interface with a single method is a function.** Once a
language has first-class functions, you don't need a class hierarchy to say "plug a behaviour
in here":

```
CLASSIC                                   MODERN
───────                                   ──────
class LRSchedule(ABC): lr(epoch)          type Schedule = Callable[[int], float]
class StepDecay(LRSchedule): ...          partial(step_decay, base=0.4, every=2, gamma=0.5)

class Trainer(ABC):                       def fit(step, *, epochs, schedule, callbacks):
    fit()          ← the skeleton             for epoch ...: schedule → step → callbacks
    train_step()   ← subclass fills it
class StubTrainer(Trainer): ...           fit(StubModel().step, ...)   ← passed in, no subclass

class Callback(ABC): update(...)          type Callback = Callable[[int, float, float], None]
trainer.attach(History())                 callbacks=[lambda e, lr, loss: losses.append(loss)]
```

## Classic → modern

| Pattern | Classic (`classic.py`) | Modern (`modern.py`) | What does the work instead |
|---|---|---|---|
| **Strategy** | `LRSchedule` ABC, one subclass per algorithm, parameters kept in `__init__` | any `epoch -> lr` function; parameters bound with `partial` | first-class functions, `functools.partial` |
| **Template Method** | abstract `Trainer.fit()` skeleton; `StubTrainer` overrides `train_step()` | `fit(step, ...)` receives the varying step as an argument | composition, which here is just Strategy again |
| **Observer** | `Callback` ABC; subject keeps `_callbacks` with `attach()` / `_notify()` | `callbacks=` is a list of callables, and notifying means calling each one | callables, closures, lambdas |

The Template Method row is the one to notice. GoF describe Template Method as varying a step
through *inheritance* and Strategy as varying it through *delegation*. Once the step can be
passed in as a function, the two patterns become the same thing: a function with a parameter.

## Why it works

- **The roles survive and the ceremony goes.** [ARCHITECTURE.md](ARCHITECTURE.md) shows the
  same roles in both diagrams. Only the inheritance arrows change, into structural conformance.
- **A new strategy is one function.** `ConstantLR` was a class with an `__init__` that stored
  one float. Its modern replacement is `lambda _: 0.1`, and it doesn't need a name.
- **Nothing to inherit, so nothing to couple to.** `StubModel` doesn't import `Trainer`. Any
  object with an `lr -> loss` method can be trained, including a bound method of an object
  that has never heard of `fit`.
- **The same check covers both.** `Schedule`, `Step` and `Callback` are type aliases, so
  `mypy --strict` checks a lambda's signature as strictly as it checks a subclass's method.

## The price

- **Signatures say less than names.** In `Callable[[int, float, float], None]`, which float is
  `lr` and which is `loss`? A callback that swaps them still type-checks. The classic
  `update(epoch, lr, loss)` names them. (Fix: a callback `Protocol`; see *Variants*.)
- **Anonymous code is harder to debug.** A failing lambda shows up as `<lambda>` in a
  traceback, and the IDE can't list "all schedules" the way it lists subclasses of `LRSchedule`.
- **Observer stays one-way in both shapes.** A callback can watch but can't stop training. Once
  it needs to, the contract changes (exercise 2).

## When the classic still wins

The modern form wins while a strategy is *one stateless method*. Each condition below breaks that:

- **The strategy has state, or more than one method.** PyTorch's `StepLR` is a class because it
  tracks `last_epoch`, offers `get_last_lr()`, and must `state_dict()` itself into a
  checkpoint. A `nonlocal` closure can hold state, but it can't explain or save it.
- **It must be pickled.** Checkpoints and multiprocessing pickle things. `StepDecay(...)` and
  `partial(step_decay, ...)` pickle; `lambda _: 0.1` and the `log_to(out)` closure fail
  (verified). PyTorch's `LambdaLR` documents exactly this: its `state_dict()` saves the
  lambda only when it is a callable object.
- **The observer listens to many events.** Hugging Face's `TrainerCallback` has more than
  a dozen `on_*` hooks. A class groups them under one name, which a loose bag of functions can't do.
- **The framework owns the loop.** Lightning's `LightningModule` is Template Method on
  purpose. Subclassing makes the hooks discoverable (your IDE lists what you can override), and
  the framework can add hooks without breaking your code.

## Variants worth naming

- **Callback protocol.** `class Callback(Protocol): def __call__(self, epoch: int, *, lr: float,
  loss: float) -> None: ...` gives a callable named, keyword-only parameters. Plain lambdas
  still satisfy it, so this fixes the first item under *The price* without bringing back
  inheritance.
- **Callable object.** A class with `__call__` sits halfway between the two shapes. It keeps
  state and pickles like the classic form, while callers still treat it as a function. This is
  what `LambdaLR` asks for.
- **`partial` vs factory closure.** `partial(step_decay, ...)` and `log_to(out)` both bind
  configuration ahead of time. `partial` pickles (when the function it wraps is module-level)
  and shows its arguments in `repr`; a closure hides them.
- **Pub/sub.** Observer with a broker in the middle, so publishers and subscribers never meet.
  See [module communication](../../codebase-pattern/module-communication/README.md).

## Where you meet it

- `sorted(key=...)`, `max(key=...)`, and `re.sub` with a function as `repl`: Strategy as a
  function, in the stdlib.
- `threading.Thread`: its docs offer both shapes. Pass `target=fn` (modern), or subclass and
  override `run()` (Template Method).
- PyTorch: `StepLR` (classic Strategy class) next to `LambdaLR(optimizer, lr_lambda=fn)`
  (a function wrapped back into one).
- Keras / Hugging Face: `callbacks=[...]` lists, with class-based callbacks for many events.
- `unittest.TestCase.setUp` (Template Method hooks) vs pytest fixtures (composition).

## Exercises

1. **Add a schedule.** Add linear warmup (`lr` rising to `base` over `n` epochs) to both files.
   Count the lines you touch in each.
2. **Early stopping.** Stop training once the loss drops below `0.3`. Callbacks return `None`,
   so how does one of them reach back into the loop? In Keras the callback sets
   `self.model.stop_training = True`; in Hugging Face it sets `control.should_training_stop`.
   Implement one way in each file. Is the observer still just an observer?
3. **A schedule with memory.** Halve the learning rate whenever the loss failed to improve. The
   `epoch -> lr` signature can no longer express it. Change it in both files. At what point does
   the modern function stop being the simpler one?
4. **Checkpoint it.** `pickle.dumps` every schedule and callback in both files. Predict which
   fail before you run it. Then make the modern constant schedule picklable without adding a class.
