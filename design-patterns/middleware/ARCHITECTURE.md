# Middleware: architecture

UML for both shapes of the toy. In the classic diagram, three patterns produce three classes
with an identical outline: each implements `Handler` and holds a `Handler`. The modern diagram
turns that shared outline into one type, `Middleware = Handler -> Handler`.

## Participants

| Pattern | GoF participant | `classic.py` | `modern.py` |
|---|---|---|---|
| Decorator | Component | `Handler` (ABC) | `Handler`, a `Callable` type alias |
| | ConcreteComponent | `ReportEndpoint` | `report`, a nested function in `run()` |
| | ConcreteDecorator | `LoggingDecorator` (holds `_component`) | `logged()` closure (holds `next_handler`) |
| Chain of Responsibility | Handler | `Handler` (ABC) | `Handler` |
| | ConcreteHandler | `AuthHandler` (holds `_successor`) | `require_user()` closure (holds `next_handler`) |
| | Client | `run()` nests the objects | `stack()` folds a list of middleware |
| Proxy | Subject | `Handler` (ABC) | `Handler` |
| | RealSubject | `ReportEndpoint` | `report` |
| | Proxy | `CachingProxy` (holds `_subject`, `_cache`) | `cached_by_path()` closure (holds `next_handler`, `cache`) |

GoF give their Decorator an abstract `Decorator` base class that forwards every call by
default. With only one concrete decorator it would just pass calls through, so `classic.py`
leaves it out.

## Classic: three classes with one outline

```mermaid
classDiagram
    direction LR

    class Handler {
        <<abstract>>
        +handle(request: Request) Response*
    }
    class ReportEndpoint {
        +calls: int
        +handle(request: Request) Response
    }

    namespace DecoratorPattern {
        class LoggingDecorator {
            -_component: Handler
            -_out: list~str~
            +handle(request: Request) Response
        }
    }
    namespace ChainOfResponsibility {
        class AuthHandler {
            -_successor: Handler
            +handle(request: Request) Response
        }
    }
    namespace ProxyPattern {
        class CachingProxy {
            -_subject: Handler
            -_cache: dict~str, Response~
            +handle(request: Request) Response
        }
    }

    Handler <|-- ReportEndpoint
    Handler <|-- LoggingDecorator
    Handler <|-- AuthHandler
    Handler <|-- CachingProxy
    LoggingDecorator o-- Handler : component
    AuthHandler o-- Handler : successor
    CachingProxy o-- Handler : subject
```

Three `o--` arrows go back to `Handler` under three different names. The recursion lives
in that loop back to the base class: any handler can wrap any other.

## Modern: one type, three functions that have it

```mermaid
classDiagram
    direction LR

    class Handler {
        <<type alias>>
        +__call__(request: Request) Response
    }
    class Middleware {
        <<type alias>>
        +__call__(next_handler: Handler) Handler
    }
    class logged {
        <<function>>
        +logged(next_handler, *, out) Handler
    }
    class require_user {
        <<function>>
        +require_user(next_handler) Handler
    }
    class cached_by_path {
        <<function>>
        +cached_by_path(next_handler) Handler
    }
    class stack {
        <<function>>
        +stack(endpoint, *middleware) Handler
    }
    class report {
        <<function>>
        +report(request) Response
    }

    logged ..|> Middleware : via partial(out=...)
    require_user ..|> Middleware
    cached_by_path ..|> Middleware
    report ..|> Handler
    Middleware ..> Handler : takes one, returns one
    stack ..> Middleware : folds with reduce

    note for stack "stack(e, a, b) == a(b(e))"
```

All three patterns satisfy `Middleware`. In the modern diagram they differ only in name,
which matches the point that they differ only in intent.

## Runtime: four requests through the onion

```mermaid
sequenceDiagram
    participant C as client
    participant L as logged
    participant A as require_user
    participant P as cached_by_path
    participant E as report

    C->>L: alice GET /report
    L->>A: call on
    A->>P: has a user, call on
    P->>E: cache miss
    E-->>L: 200 (stored in cache on the way back)

    C->>L: anonymous GET /report
    L->>A: call on
    A-->>L: 401, chain stops here

    C->>L: bob GET /report
    L->>A: call on
    A->>P: has a user, call on
    P-->>L: 200 from cache, endpoint not called

    C->>L: bob GET /audit
    L->>A: call on
    A->>P: has a user, call on
    P->>E: cache miss
    E-->>L: 200
```

The classic file runs the same sequence. Replace each participant with its class
(`LoggingDecorator`, `AuthHandler`, `CachingProxy`, `ReportEndpoint`) and each call with
`.handle(request)`.
