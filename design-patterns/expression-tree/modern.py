#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Expression tree, MODERN shape: the same four patterns, absorbed by data + pattern matching.

    Composite   -> frozen dataclasses that hold other nodes; `Expr` is their union
    Interpreter -> evaluate(): one function with a `match` case per node type
    Visitor     -> show() and simplify(): more functions of the same shape, no accept() needed
    Iterator    -> walk(): a generator; the paused function remembers where the traversal is

Open next to classic.py: the scenario is the same and so is the transcript.

Run:  uv run modern.py
"""
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import assert_never


# ── Composite: nodes are plain data ──────────────────────────────────────────

@dataclass(frozen=True)
class Num:
    value: float


@dataclass(frozen=True)
class Var:
    name: str


@dataclass(frozen=True)
class Add:
    left: "Expr"
    right: "Expr"


@dataclass(frozen=True)
class Mul:
    left: "Expr"
    right: "Expr"


type Expr = Num | Var | Add | Mul


# ── Interpreter: one function, one case per node type ────────────────────────

def evaluate(e: Expr, env: Mapping[str, float]) -> float:
    match e:
        case Num(value):
            return value
        case Var(name):
            return env[name]
        case Add(left, right):
            return evaluate(left, env) + evaluate(right, env)
        case Mul(left, right):
            return evaluate(left, env) * evaluate(right, env)
        case _:
            assert_never(e)                     # mypy flags any node type left unhandled


# ── Visitor -> just more functions of the same shape ─────────────────────────

def show(e: Expr) -> str:
    match e:
        case Num(value):
            return f"{value:g}"
        case Var(name):
            return name
        case Add(left, right):
            return f"{_operand(left)} + {_operand(right)}"
        case Mul(left, right):
            return f"{_operand(left)} * {_operand(right)}"
        case _:
            assert_never(e)


def _operand(e: Expr) -> str:
    return f"({show(e)})" if isinstance(e, Add | Mul) else show(e)


def simplify(e: Expr) -> Expr:
    # 1. Simplify the children first, and rebuild the node from them.
    match e:
        case Add(left, right):
            e = Add(simplify(left), simplify(right))
        case Mul(left, right):
            e = Mul(simplify(left), simplify(right))
    # 2. Each rule is one nested pattern: it looks at the node and its children at once.
    match e:
        case Add(Num(a), Num(b)):
            return Num(a + b)
        case Mul(Num(a), Num(b)):
            return Num(a * b)
        case Add(x, Num(0)) | Add(Num(0), x):
            return x
        case Mul(_, Num(0)) | Mul(Num(0), _):
            return Num(0)
        case Mul(x, Num(1)) | Mul(Num(1), x):
            return x
        case _:
            return e


# ── Iterator -> a generator ──────────────────────────────────────────────────

def walk(e: Expr) -> Iterator[Expr]:
    """Parent before children, left before right."""
    yield e
    match e:
        case Add(left, right) | Mul(left, right):
            yield from walk(left)
            yield from walk(right)


# ── Composition root ─────────────────────────────────────────────────────────

def run() -> list[str]:
    expr = Add(Mul(Add(Var("x"), Num(0)), Num(1)), Mul(Num(2), Num(3)))   # ((x + 0) * 1) + (2 * 3)
    env = {"x": 4}
    simple = simplify(expr)
    return [
        f"expression  {show(expr)}",
        f"evaluate    {evaluate(expr, env):g}   (x = 4)",
        f"simplified  {show(simple)}",
        f"evaluate    {evaluate(simple, env):g}   (unchanged)",
        f"preorder    {' '.join(type(node).__name__ for node in walk(expr))}",
        f"nodes       {sum(1 for _ in walk(expr))} → {sum(1 for _ in walk(simple))}",
        f"variables   {sorted({node.name for node in walk(expr) if isinstance(node, Var)})}",
    ]


if __name__ == "__main__":
    print("\n".join(run()))
