#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Middleware, CLASSIC shape: three GoF patterns as the book draws them.

    Decorator               : LoggingDecorator wraps a Handler, adds behaviour, always passes on
    Chain of Responsibility : AuthHandler answers the request itself, or passes it to its successor
    Proxy                   : CachingProxy stands in for the real endpoint and decides when to call it

All three are a Handler holding a Handler. They differ only in intent, and in what GoF named
the field: component, successor, subject.

Open next to modern.py: the scenario is the same and so is the transcript.

Run:  uv run classic.py
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class Request:
    path: str
    user: str | None = None


@dataclass(frozen=True)
class Response:
    status: int
    body: str


# ── The one interface every participant implements ───────────────────────────

class Handler(ABC):
    @abstractmethod
    def handle(self, request: Request) -> Response: ...


# ── Real subject: the endpoint the whole stack exists to protect ─────────────

class ReportEndpoint(Handler):
    def __init__(self) -> None:
        self.calls = 0

    def handle(self, request: Request) -> Response:
        self.calls += 1
        return Response(200, f"contents of {request.path}")


# ── Decorator: wrap a component and add behaviour around it ──────────────────

class LoggingDecorator(Handler):
    def __init__(self, component: Handler, out: list[str]) -> None:
        self._component, self._out = component, out

    def handle(self, request: Request) -> Response:
        response = self._component.handle(request)
        who = request.user or "anonymous"
        self._out.append(f"{who:<10} GET {request.path:<8} → {response.status} {response.body}")
        return response


# ── Chain of Responsibility: handle the request, or pass it down the chain ──

class AuthHandler(Handler):
    def __init__(self, successor: Handler) -> None:
        self._successor = successor

    def handle(self, request: Request) -> Response:
        if request.user is None:
            return Response(401, "login required")     # handled here: the chain stops
        return self._successor.handle(request)


# ── Proxy: same interface as the real subject, controls access to it ─────────

class CachingProxy(Handler):
    def __init__(self, subject: Handler) -> None:
        self._subject = subject
        self._cache: dict[str, Response] = {}

    def handle(self, request: Request) -> Response:
        if request.path not in self._cache:
            self._cache[request.path] = self._subject.handle(request)
        return self._cache[request.path]


# ── Composition root: nest the objects, outermost first ──────────────────────

REQUESTS = [
    Request("/report", "alice"),
    Request("/report"),                         # nobody logged in
    Request("/report", "bob"),                  # same path as alice: served from cache
    Request("/audit", "bob"),
]


def run() -> list[str]:
    out: list[str] = []
    endpoint = ReportEndpoint()
    app = LoggingDecorator(AuthHandler(CachingProxy(endpoint)), out)
    for request in REQUESTS:
        app.handle(request)
    out.append(f"endpoint ran {endpoint.calls} times for {len(REQUESTS)} requests")
    return out


if __name__ == "__main__":
    print("\n".join(run()))
