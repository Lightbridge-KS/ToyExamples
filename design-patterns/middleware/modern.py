#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Middleware, MODERN shape: the same three patterns as functions that wrap functions.

    Decorator               -> logged():         adds behaviour around the call it wraps
    Chain of Responsibility -> require_user():   may return early instead of calling on
    Proxy                   -> cached_by_path(): decides whether the real handler runs at all

Each is a `Handler -> Handler` function, which is exactly what Python's @decorator syntax
applies. A middleware stack is a set of decorators applied at runtime.

Open next to classic.py: the scenario is the same and so is the transcript.

Run:  uv run modern.py
"""
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial, reduce, wraps


@dataclass(frozen=True)
class Request:
    path: str
    user: str | None = None


@dataclass(frozen=True)
class Response:
    status: int
    body: str


type Handler = Callable[[Request], Response]
type Middleware = Callable[[Handler], Handler]


# ── Decorator: wrap a handler and add behaviour around it ────────────────────

def logged(next_handler: Handler, *, out: list[str]) -> Handler:
    @wraps(next_handler)
    def handler(request: Request) -> Response:
        response = next_handler(request)
        who = request.user or "anonymous"
        out.append(f"{who:<10} GET {request.path:<8} → {response.status} {response.body}")
        return response
    return handler


# ── Chain of Responsibility: answer here, or call the next link ──────────────

def require_user(next_handler: Handler) -> Handler:
    @wraps(next_handler)
    def handler(request: Request) -> Response:
        if request.user is None:
            return Response(401, "login required")     # handled here: the chain stops
        return next_handler(request)
    return handler


# ── Proxy: stand in for the real handler and decide when to call it ──────────

def cached_by_path(next_handler: Handler) -> Handler:
    cache: dict[str, Response] = {}             # closure state: one cache per wrapped handler

    @wraps(next_handler)
    def handler(request: Request) -> Response:
        if request.path not in cache:
            cache[request.path] = next_handler(request)
        return cache[request.path]
    return handler


def stack(endpoint: Handler, *middleware: Middleware) -> Handler:
    """Wrap `endpoint` so the first middleware listed is the outermost: stack(e, a, b) == a(b(e))."""
    return reduce(lambda inner, wrap: wrap(inner), reversed(middleware), endpoint)


# ── Composition root: list the middleware, outermost first ───────────────────

REQUESTS = [
    Request("/report", "alice"),
    Request("/report"),                         # nobody logged in
    Request("/report", "bob"),                  # same path as alice: served from cache
    Request("/audit", "bob"),
]


def run() -> list[str]:
    out: list[str] = []
    calls: list[str] = []

    def report(request: Request) -> Response:  # the real subject is just a function
        calls.append(request.path)
        return Response(200, f"contents of {request.path}")

    app = stack(report, partial(logged, out=out), require_user, cached_by_path)
    for request in REQUESTS:
        app(request)
    out.append(f"endpoint ran {len(calls)} times for {len(REQUESTS)} requests")
    return out


if __name__ == "__main__":
    print("\n".join(run()))
