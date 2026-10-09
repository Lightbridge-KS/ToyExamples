# Expression tree: Composite, Interpreter, Visitor, Iterator (toy example)

*`((x + 0) * 1) + (2 * 3)` is evaluated, printed, simplified to `x + 6`, and walked. The same
scenario is written twice: as the GoF book draws it (114 lines of code, 9 classes) and in
modern Python (84 lines, 4 frozen dataclasses). The two files produce the same transcript.*

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

A tree of a few fixed node types is a **sum type**: an `Expr` is a `Num`, *or* a `Var`, *or*
an `Add`, *or* a `Mul`. Python 3.10+ can express that directly with frozen dataclasses, a
union, and `match`. Each of the four patterns then turns into something smaller:

```
CLASSIC                                        MODERN
───────                                        ──────
class Expr(ABC): interpret, accept, children   type Expr = Num | Var | Add | Mul

class Add(Expr):                               @dataclass(frozen=True)
    interpret(env): left.interpret + ...       class Add: left: Expr; right: Expr
    accept(v): return v.visit_add(self)
    children(): [left, right]                  def evaluate(e, env): match e: case Add(l, r): ...

class Simplifier(ExprVisitor[Expr]):           def simplify(e):
    visit_add(node):                               match e:
        if isinstance(right, Num) and                  case Add(x, Num(0)): return x
           right.value == 0: return left

class PreorderIterator: _stack, __next__       def walk(e): yield e; yield from walk(...)
```

The `simplify` row is the one to look at. A simplification rule is about a node **and its
children** together ("an `Add` whose right child is `Num(0)`"). Double dispatch only resolves
the *outer* node's class, so every classic rule falls back to `isinstance` checks on the
children. A nested pattern states the rule in exactly that shape.

## Classic → modern

| Pattern | Classic (`classic.py`) | Modern (`modern.py`) | What does the work instead |
|---|---|---|---|
| **Composite** | `Expr` ABC; `Add`/`Mul` override `children()`, leaves return `[]` | frozen dataclasses whose fields are `Expr`; `Expr` is their union | dataclasses + `type` alias union |
| **Interpreter** | `interpret(env)` defined on each of the 4 node classes | `evaluate(e, env)`, one function with 4 cases | `match` with class patterns |
| **Visitor** | `accept()` on each node + `ExprVisitor[T]` with 4 `visit_*` methods, one subclass per operation | one function per operation: `show()`, `simplify()` | `match`; `assert_never` for exhaustiveness |
| **Iterator** | `PreorderIterator` with an explicit stack and `__next__` | `walk()`: `yield` + `yield from` | generators |

## Why it works

- **An operation is a function.** Adding `derivative()` means writing one function. The
  classic shape needs a new `Visitor` subclass with four methods, and only works because
  every node already carries an `accept()` stub.
- **Rules read the way you'd say them.** `case Mul(_, Num(0)) | Mul(Num(0), _): return Num(0)`
  says "anything times zero is zero" in one line. Its classic equivalent is a compound
  `isinstance` condition.
- **The type checker counts the cases.** Add a node type to the union, and mypy flags every
  `assert_never` that can now be reached (verified: `evaluate` and `show`).
- **Equality and hashing come free.** Frozen dataclasses compare by value:
  `Add(Var("x"), Num(1)) == Add(Var("x"), Num(1))` is `True`. The classic nodes compare by
  identity, so the same check is `False` (verified; exercise 3).
- **The traversal state is the paused function.** `walk()` has no stack field and no
  `StopIteration`. Python keeps the place inside the suspended generator.

## The price

This toy is the clearest case of the **expression problem**. You can make it easy to add
*operations* or easy to add *node types*, but not both:

| Add… | Classic: methods on nodes (Interpreter) | Classic: Visitor | Modern: `match` functions |
|---|---|---|---|
| an operation | edit every node class | one new visitor class | one new function |
| a node type | one new class | edit every visitor | edit every function |

The modern shape sits with Visitor: operations are cheap and node types are expensive. There
are two more costs:

- **A catch-all hides gaps.** After adding a `Neg` node, mypy flagged `evaluate` and `show`,
  but not `simplify` (its `case _` swallows the new node) or `walk` (which would quietly stop
  descending). Exhaustiveness checking covers only the functions that end in `assert_never`.
- **Recursion has a depth limit.** On a tree 10,000 levels deep, `walk()` and `evaluate()`
  raise `RecursionError`. So does the classic `interpret()`. Only `PreorderIterator`, which
  keeps its own stack, survives (verified; exercise 4).

## When the classic still wins

- **Many node types, few that matter.** Python's `ast` has about a hundred node classes.
  `ast.NodeVisitor` lets you write `visit_Call` alone, and `generic_visit` walks everything
  else. With `match`, a pass that cares about one node type still needs recursion written
  out for all the others.
- **An open set of node types.** If plugins must add nodes, a closed union can't list them.
  Methods on the nodes (Interpreter style) stay open, and so does `functools.singledispatch`
  (see *Variants*).
- **Deep inputs.** For untrusted or very deep trees, an explicit stack is the only form here
  that doesn't hit the recursion limit.

## Variants worth naming

- **`functools.singledispatch`.** `@singledispatch def show(e)` plus `@show.register` per type
  gives one function per operation (like `match`) that third parties can extend with new
  types (like methods). Dispatch looks only at the *outer* argument's type, so it can't
  express nested rules.
- **Reflective visitor.** `ast.NodeVisitor` dispatches on `"visit_" + type(node).__name__`. It
  needs no `accept()` on the nodes, at the price of a string lookup and no static check.
- **Rewriting visitor.** `ast.NodeTransformer` returns replacement nodes, the classic version
  of `simplify()`.

## Where you meet it

- Python's `ast`: `NodeVisitor` / `NodeTransformer` (the classic Visitor, in the stdlib) next to
  `ast.walk` (a generator that yields every node, in no specified order).
- Rust `enum` + `match`, TypeScript discriminated unions + `switch`, Kotlin sealed classes +
  `when`: the modern shape exists in other languages too.
- SymPy expression trees, with `preorder_traversal`; SQL compilers; linters and codemods
  (LibCST visitors).

## Exercises

1. **Add an operation.** Write `derivative(e, var)` in both files. How many classes did each
   file gain?
2. **Add a node type.** Add `Neg(operand)` to both files. In `modern.py`, add it to the union
   first and run `uvx mypy --strict modern.py` before writing any case. Which functions did it
   flag, and which did it miss?
3. **Add a rule.** Rewrite `x + x` as `2 * x`. In modern code that's a guard:
   `case Add(a, b) if a == b`. Write the same rule in `Simplifier.visit_add`. Why does `==`
   fail for classic nodes?
4. **Go deep.** Build 10,000 nested `Add`s and iterate the result with `PreorderIterator` and
   with `walk`. Then write a `walk` that survives the depth without becoming a class.
