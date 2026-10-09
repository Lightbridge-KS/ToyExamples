#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Training loop, CLASSIC shape: three GoF patterns as the book draws them.

    Strategy        : LRSchedule subclasses, picked by the caller, swapped without touching fit()
    Template Method : Trainer.fit() is the fixed skeleton; a subclass fills in train_step()
    Observer        : Callback subclasses attached to the trainer, notified after each epoch

Open next to modern.py: the scenario is the same and so is the transcript.

Run:  uv run classic.py
"""
from abc import ABC, abstractmethod


# ── Strategy: one interface, interchangeable algorithms ──────────────────────
# Every schedule is a class, even though each one has a single method.

class LRSchedule(ABC):
    @abstractmethod
    def lr(self, epoch: int) -> float: ...


class ConstantLR(LRSchedule):
    def __init__(self, lr: float) -> None:
        self._lr = lr

    def lr(self, epoch: int) -> float:
        return self._lr


class StepDecay(LRSchedule):
    """Multiply the base rate by `gamma` every `every` epochs."""

    def __init__(self, base: float, every: int, gamma: float) -> None:
        self._base = base
        self._every = every
        self._gamma = gamma

    def lr(self, epoch: int) -> float:
        return self._base * self._gamma ** (epoch // self._every)


# ── Observer: subscribers the subject notifies ───────────────────────────────

class Callback(ABC):
    @abstractmethod
    def update(self, epoch: int, lr: float, loss: float) -> None: ...


class PrintLogger(Callback):
    def __init__(self, out: list[str]) -> None:
        self._out = out

    def update(self, epoch: int, lr: float, loss: float) -> None:
        self._out.append(f"epoch {epoch}  lr={lr:.3f}  loss={loss:.4f}")


class History(Callback):
    def __init__(self) -> None:
        self.losses: list[float] = []

    def update(self, epoch: int, lr: float, loss: float) -> None:
        self.losses.append(loss)


# ── Template Method: a fixed skeleton whose steps subclasses fill in ─────────
# Trainer is also the Observer *subject*: it owns the subscriber list.

class Trainer(ABC):
    def __init__(self, schedule: LRSchedule) -> None:
        self._schedule = schedule               # Strategy: held, not chosen here
        self._callbacks: list[Callback] = []

    def attach(self, callback: Callback) -> None:
        self._callbacks.append(callback)

    def fit(self, epochs: int) -> None:
        """The template method. Subclasses never override this; they fill its blanks."""
        self.on_fit_start()
        for epoch in range(epochs):
            lr = self._schedule.lr(epoch)
            loss = self.train_step(lr)
            self._notify(epoch, lr, loss)

    @abstractmethod
    def train_step(self, lr: float) -> float:
        """A primitive operation: every subclass MUST provide it."""

    def on_fit_start(self) -> None:
        """A hook: a subclass MAY override it. The default does nothing."""

    def _notify(self, epoch: int, lr: float, loss: float) -> None:
        for callback in self._callbacks:
            callback.update(epoch, lr, loss)


class StubTrainer(Trainer):
    """A stand-in for forward, backward and optimizer: each step shrinks the loss by `lr`."""

    def on_fit_start(self) -> None:
        self.loss = 1.0

    def train_step(self, lr: float) -> float:
        self.loss *= 1 - lr
        return self.loss


# ── Composition root: pick a strategy, attach observers, run the template ────

def run() -> list[str]:
    out: list[str] = []
    schedules = {
        "constant": ConstantLR(0.1),
        "step decay": StepDecay(base=0.4, every=2, gamma=0.5),
    }
    for name, schedule in schedules.items():
        out.append(f"── {name} ──")
        trainer = StubTrainer(schedule)
        history = History()
        trainer.attach(PrintLogger(out))
        trainer.attach(history)
        trainer.fit(epochs=4)
        out.append(f"best loss {min(history.losses):.4f}")
    return out


if __name__ == "__main__":
    print("\n".join(run()))
