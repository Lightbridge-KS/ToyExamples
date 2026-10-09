#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Training loop, MODERN shape: the same three patterns, absorbed by first-class functions.

    Strategy        -> a function:             schedule: Callable[[int], float]
    Template Method -> a function that takes, as an argument, the step it used to defer to a subclass
    Observer        -> a list of callables:    callbacks: Sequence[Callback]

Open next to classic.py: the scenario is the same and so is the transcript.

Run:  uv run modern.py
"""
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import partial

type Schedule = Callable[[int], float]               # epoch -> lr
type Step = Callable[[float], float]                 # lr -> loss
type Callback = Callable[[int, float, float], None]  # (epoch, lr, loss) -> None


# ── Strategy: a schedule is any function from epoch to lr ────────────────────
# No base class. A constant schedule doesn't even need a name: `lambda _: 0.1`.

def step_decay(epoch: int, *, base: float, every: int, gamma: float) -> float:
    """Multiply the base rate by `gamma` every `every` epochs."""
    return base * gamma ** (epoch // every)


# ── Observer: a subscriber is any function with the right signature ──────────

def log_to(out: list[str]) -> Callback:
    def log(epoch: int, lr: float, loss: float) -> None:
        out.append(f"epoch {epoch}  lr={lr:.3f}  loss={loss:.4f}")
    return log


# ── Template Method -> composition ───────────────────────────────────────────
# The skeleton is the same loop. The step that varies comes in as an argument,
# so no subclass is needed. The subscriber list is just a parameter.

def fit(step: Step, *, epochs: int, schedule: Schedule,
        callbacks: Sequence[Callback] = ()) -> None:
    for epoch in range(epochs):
        lr = schedule(epoch)
        loss = step(lr)
        for callback in callbacks:
            callback(epoch, lr, loss)


@dataclass
class StubModel:
    """A stand-in for forward, backward and optimizer: each step shrinks the loss by `lr`.

    It inherits from nothing. `fit` only needs `model.step`, a bound method,
    which is just another `lr -> loss` callable. The old `on_fit_start` hook is
    gone: a fresh model starts at a loss of 1.0.
    """
    loss: float = 1.0

    def step(self, lr: float) -> float:
        self.loss *= 1 - lr
        return self.loss


# ── Composition root: pass the strategy and the observers in as arguments ────

def run() -> list[str]:
    out: list[str] = []
    schedules: dict[str, Schedule] = {
        "constant": lambda _: 0.1,
        "step decay": partial(step_decay, base=0.4, every=2, gamma=0.5),
    }
    for name, schedule in schedules.items():
        out.append(f"── {name} ──")
        losses: list[float] = []
        fit(StubModel().step, epochs=4, schedule=schedule,
            callbacks=[log_to(out), lambda epoch, lr, loss: losses.append(loss)])
        out.append(f"best loss {min(losses):.4f}")
    return out


if __name__ == "__main__":
    print("\n".join(run()))
