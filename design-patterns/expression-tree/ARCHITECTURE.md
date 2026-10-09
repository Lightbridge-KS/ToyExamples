# Expression tree: architecture

UML for both shapes of the toy. In the classic shape the node classes are busy. Each one
evaluates itself (Interpreter), dispatches visitors (Visitor), and reports its children
(Composite, used by Iterator). In the modern shape the nodes are plain data, and every
operation is a function outside them.

## Participants

| Pattern | GoF participant | `classic.py` | `modern.py` |
|---|---|---|---|
| Composite | Component | `Expr` (ABC) | `Expr`, a union type alias |
| | Leaf | `Num`, `Var` | `Num`, `Var` (frozen dataclasses) |
| | Composite | `Add`, `Mul`, which override `children()` | `Add`, `Mul`, whose fields are `Expr` |
| Interpreter | AbstractExpression | `Expr.interpret(env)` | `evaluate(e, env)` |
| | TerminalExpression | `Num`, `Var` | `case Num(...)`, `case Var(...)` |
| | NonterminalExpression | `Add`, `Mul` | `case Add(...)`, `case Mul(...)` |
| | Context | `env: Mapping[str, float]` | `env: Mapping[str, float]` |
| Visitor | Visitor | `ExprVisitor[T]` with 4 `visit_*` methods | gone: an operation is just a function |
| | ConcreteVisitor | `Printer`, `Simplifier` | `show()`, `simplify()` |
| | Element | `Expr.accept(visitor)` on each node | gone: `match` dispatches on the node itself |
| Iterator | ConcreteIterator | `PreorderIterator` (explicit `_stack`) | `walk()` (a generator) |
| | Aggregate | `Expr.children()` | the `Add` / `Mul` fields, read by `match` |

## Classic: every node carries every pattern

```mermaid
classDiagram
    direction TB

    namespace CompositeAndInterpreter {
        class Expr {
            <<abstract>>
            +interpret(env) float*
            +accept(visitor: ExprVisitor~T~) T*
            +children() list~Expr~
        }
        class Num {
            +value: float
        }
        class Var {
            +name: str
        }
        class Add {
            +left: Expr
            +right: Expr
            +children() list~Expr~
        }
        class Mul {
            +left: Expr
            +right: Expr
            +children() list~Expr~
        }
    }

    namespace VisitorPattern {
        class ExprVisitor~T~ {
            <<abstract>>
            +visit_num(node: Num) T*
            +visit_var(node: Var) T*
            +visit_add(node: Add) T*
            +visit_mul(node: Mul) T*
        }
        class Printer {
            +visit_num/var/add/mul() str
        }
        class Simplifier {
            +visit_num/var/add/mul() Expr
        }
    }

    namespace IteratorPattern {
        class PreorderIterator {
            -_stack: list~Expr~
            +__next__() Expr
        }
    }

    Expr <|-- Num
    Expr <|-- Var
    Expr <|-- Add
    Expr <|-- Mul
    Add o-- "2" Expr : left, right
    Mul o-- "2" Expr : left, right
    ExprVisitor <|-- Printer
    ExprVisitor <|-- Simplifier
    Expr ..> ExprVisitor : accept() calls back
    ExprVisitor ..> Expr : visit_* takes each node class
    PreorderIterator ..> Expr : children()
```

`Expr` and `ExprVisitor` depend on each other. This loop is the double-dispatch handshake:
each node class names a visitor method, and each visitor method names a node class. Adding a
node type means changing both sides.

## Modern: data in the middle, functions around it

```mermaid
classDiagram
    direction TB

    class Expr {
        <<type alias>>
        Num | Var | Add | Mul
    }
    class Num {
        <<frozen dataclass>>
        +value: float
    }
    class Var {
        <<frozen dataclass>>
        +name: str
    }
    class Add {
        <<frozen dataclass>>
        +left: Expr
        +right: Expr
    }
    class Mul {
        <<frozen dataclass>>
        +left: Expr
        +right: Expr
    }
    class evaluate {
        <<function>>
        +evaluate(e: Expr, env) float
    }
    class show {
        <<function>>
        +show(e: Expr) str
    }
    class simplify {
        <<function>>
        +simplify(e: Expr) Expr
    }
    class walk {
        <<generator>>
        +walk(e: Expr) Iterator~Expr~
    }

    Num ..|> Expr
    Var ..|> Expr
    Add ..|> Expr
    Mul ..|> Expr
    Add o-- "2" Expr : left, right
    Mul o-- "2" Expr : left, right
    evaluate ..> Expr : match
    show ..> Expr : match
    simplify ..> Expr : match, nested patterns
    walk ..> Expr : match

    note for Expr "nodes know nothing about the operations on them"
```

Every dependency arrow now points *into* the data. The nodes import nothing, and each
operation stands alone, so deleting `show()` breaks nothing else.

## Runtime: simplifying `x + 0`

Classic needs two dispatches to reach the right method, then runs `isinstance` checks on the
children:

```mermaid
sequenceDiagram
    participant S as Simplifier
    participant A as Add node
    participant X as Var x
    participant Z as Num 0

    S->>A: accept(simplifier)
    A->>S: visit_add(self)
    S->>X: accept(simplifier)
    X-->>S: visit_var returns x
    S->>Z: accept(simplifier)
    Z-->>S: visit_num returns Num 0
    Note over S: isinstance(right, Num) and right.value == 0, so return left
```

Modern is one call per node and a pattern match on the rebuilt node:

```mermaid
sequenceDiagram
    participant R as caller
    participant F as simplify()

    R->>F: simplify(Add(Var x, Num 0))
    F->>F: simplify(Var x), simplify(Num 0)
    Note over F: rebuilt node matches case Add(x, Num(0)), so return x
    F-->>R: Var x
```
