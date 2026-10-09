#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Expression tree, CLASSIC shape: four GoF patterns as the book draws them.

    Composite   : Expr is the shared interface; Add and Mul hold child Exprs, Num and Var are leaves
    Interpreter : every node class knows how to interpret() itself against variable values
    Visitor     : Printer and Simplifier add operations without editing the node classes, using
                  double dispatch: node.accept(visitor) calls back visitor.visit_<node>(node)
    Iterator    : PreorderIterator walks the tree, keeping its place on an explicit stack

Open next to modern.py: the scenario is the same and so is the transcript.

Run:  uv run classic.py
"""
from abc import ABC, abstractmethod
from collections.abc import Mapping


# ── Composite + Interpreter: the node classes ────────────────────────────────

class Expr(ABC):
    @abstractmethod
    def interpret(self, env: Mapping[str, float]) -> float:
        """Interpreter: every node evaluates itself."""

    @abstractmethod
    def accept[T](self, visitor: "ExprVisitor[T]") -> T:
        """Visitor: hand control back to the visitor method for this node's class."""

    def children(self) -> list["Expr"]:
        """Composite: leaves have no children; composites override this."""
        return []


class Num(Expr):
    def __init__(self, value: float) -> None:
        self.value = value

    def interpret(self, env: Mapping[str, float]) -> float:
        return self.value

    def accept[T](self, visitor: "ExprVisitor[T]") -> T:
        return visitor.visit_num(self)


class Var(Expr):
    def __init__(self, name: str) -> None:
        self.name = name

    def interpret(self, env: Mapping[str, float]) -> float:
        return env[self.name]

    def accept[T](self, visitor: "ExprVisitor[T]") -> T:
        return visitor.visit_var(self)


class Add(Expr):
    def __init__(self, left: Expr, right: Expr) -> None:
        self.left, self.right = left, right

    def interpret(self, env: Mapping[str, float]) -> float:
        return self.left.interpret(env) + self.right.interpret(env)

    def accept[T](self, visitor: "ExprVisitor[T]") -> T:
        return visitor.visit_add(self)

    def children(self) -> list[Expr]:
        return [self.left, self.right]


class Mul(Expr):
    def __init__(self, left: Expr, right: Expr) -> None:
        self.left, self.right = left, right

    def interpret(self, env: Mapping[str, float]) -> float:
        return self.left.interpret(env) * self.right.interpret(env)

    def accept[T](self, visitor: "ExprVisitor[T]") -> T:
        return visitor.visit_mul(self)

    def children(self) -> list[Expr]:
        return [self.left, self.right]


# ── Visitor: one class per operation, one method per node class ──────────────

class ExprVisitor[T](ABC):
    @abstractmethod
    def visit_num(self, node: Num) -> T: ...

    @abstractmethod
    def visit_var(self, node: Var) -> T: ...

    @abstractmethod
    def visit_add(self, node: Add) -> T: ...

    @abstractmethod
    def visit_mul(self, node: Mul) -> T: ...


class Printer(ExprVisitor[str]):
    def visit_num(self, node: Num) -> str:
        return f"{node.value:g}"

    def visit_var(self, node: Var) -> str:
        return node.name

    def visit_add(self, node: Add) -> str:
        return f"{self._operand(node.left)} + {self._operand(node.right)}"

    def visit_mul(self, node: Mul) -> str:
        return f"{self._operand(node.left)} * {self._operand(node.right)}"

    def _operand(self, node: Expr) -> str:
        text = node.accept(self)
        return f"({text})" if isinstance(node, (Add, Mul)) else text


class Simplifier(ExprVisitor[Expr]):
    """Simplify the children first, then apply the rules to the rebuilt node.

    Every rule depends on a *child's* class, which double dispatch can't see,
    so each rule falls back to isinstance() checks.
    """

    def visit_num(self, node: Num) -> Expr:
        return node

    def visit_var(self, node: Var) -> Expr:
        return node

    def visit_add(self, node: Add) -> Expr:
        left, right = node.left.accept(self), node.right.accept(self)
        if isinstance(left, Num) and isinstance(right, Num):
            return Num(left.value + right.value)
        if isinstance(right, Num) and right.value == 0:
            return left
        if isinstance(left, Num) and left.value == 0:
            return right
        return Add(left, right)

    def visit_mul(self, node: Mul) -> Expr:
        left, right = node.left.accept(self), node.right.accept(self)
        if isinstance(left, Num) and isinstance(right, Num):
            return Num(left.value * right.value)
        if (isinstance(right, Num) and right.value == 0) or (isinstance(left, Num) and left.value == 0):
            return Num(0)
        if isinstance(right, Num) and right.value == 1:
            return left
        if isinstance(left, Num) and left.value == 1:
            return right
        return Mul(left, right)


# ── Iterator: an object that remembers where the traversal is ────────────────

class PreorderIterator:
    """Parent before children, left before right."""

    def __init__(self, root: Expr) -> None:
        self._stack = [root]

    def __iter__(self) -> "PreorderIterator":
        return self

    def __next__(self) -> Expr:
        if not self._stack:
            raise StopIteration
        node = self._stack.pop()
        self._stack.extend(reversed(node.children()))   # push right first, so left pops first
        return node


# ── Composition root ─────────────────────────────────────────────────────────

def run() -> list[str]:
    expr = Add(Mul(Add(Var("x"), Num(0)), Num(1)), Mul(Num(2), Num(3)))   # ((x + 0) * 1) + (2 * 3)
    env = {"x": 4}
    printer = Printer()
    simple = expr.accept(Simplifier())
    return [
        f"expression  {expr.accept(printer)}",
        f"evaluate    {expr.interpret(env):g}   (x = 4)",
        f"simplified  {simple.accept(printer)}",
        f"evaluate    {simple.interpret(env):g}   (unchanged)",
        f"preorder    {' '.join(type(node).__name__ for node in PreorderIterator(expr))}",
        f"nodes       {sum(1 for _ in PreorderIterator(expr))} → {sum(1 for _ in PreorderIterator(simple))}",
        f"variables   {sorted({node.name for node in PreorderIterator(expr) if isinstance(node, Var)})}",
    ]


if __name__ == "__main__":
    print("\n".join(run()))
