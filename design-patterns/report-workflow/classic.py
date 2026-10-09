#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Report workflow, CLASSIC shape: GoF State as the book draws it, with Observer for side effects.

    State    : one class per status. Each overrides only the events it accepts, and moves the
               report on by swapping in the next state object. Report (the context) just delegates.
    Observer : listeners attached to the report hear about every accepted event.

A radiology report: draft -> preliminary -> final -> appended. A final report is locked;
the only way to add to it is an addendum.

Open next to modern.py: the scenario is the same and so is the transcript.

Run:  uv run classic.py
"""
from abc import ABC, abstractmethod
from collections.abc import Callable


class InvalidAction(Exception):
    pass


# ── State: one class per status; the base class rejects every event ──────────

class ReportState(ABC):
    name: str

    def edit(self, report: "Report", text: str) -> None:
        raise self._reject("edit")

    def sign_preliminary(self, report: "Report") -> None:
        raise self._reject("sign_preliminary")

    def sign_final(self, report: "Report") -> None:
        raise self._reject("sign_final")

    def addend(self, report: "Report", text: str) -> None:
        raise self._reject("addend")

    def _reject(self, event: str) -> InvalidAction:
        return InvalidAction(f"cannot {event} when {self.name}")


class Draft(ReportState):
    name = "draft"

    def edit(self, report: "Report", text: str) -> None:
        report.body = text

    def sign_preliminary(self, report: "Report") -> None:
        report.state = Preliminary()

    def sign_final(self, report: "Report") -> None:
        report.state = Final()


class Preliminary(ReportState):
    name = "preliminary"

    def edit(self, report: "Report", text: str) -> None:
        report.body = text                      # same as Draft: shared behaviour is repeated

    def sign_final(self, report: "Report") -> None:
        report.state = Final()


class Final(ReportState):
    name = "final"

    def addend(self, report: "Report", text: str) -> None:
        report.addenda.append(text)
        report.state = Appended()


class Appended(ReportState):
    name = "appended"

    def addend(self, report: "Report", text: str) -> None:
        report.addenda.append(text)


# ── Observer: listeners the report notifies after each accepted event ────────

class ReportListener(ABC):
    @abstractmethod
    def on_event(self, event: str, before: str, after: str) -> None: ...


class AuditLog(ReportListener):
    def __init__(self, out: list[str]) -> None:
        self._out = out

    def on_event(self, event: str, before: str, after: str) -> None:
        self._out.append(f"audit   {event:<17}{before:<12}→ {after}")


class ReferrerNotifier(ReportListener):
    def __init__(self, out: list[str]) -> None:
        self._out = out

    def on_event(self, event: str, before: str, after: str) -> None:
        if after == "final" and before != "final":
            self._out.append("notify  referring physician: report is final")


# ── Context: holds the current state object and delegates every event to it ──

class Report:
    def __init__(self, listeners: list[ReportListener]) -> None:
        self.state: ReportState = Draft()
        self.body = ""
        self.addenda: list[str] = []
        self._listeners = listeners

    @property
    def status(self) -> str:
        return self.state.name

    def edit(self, text: str) -> None:
        self._handle("edit", lambda: self.state.edit(self, text))

    def sign_preliminary(self) -> None:
        self._handle("sign_preliminary", lambda: self.state.sign_preliminary(self))

    def sign_final(self) -> None:
        self._handle("sign_final", lambda: self.state.sign_final(self))

    def addend(self, text: str) -> None:
        self._handle("addend", lambda: self.state.addend(self, text))

    def _handle(self, event: str, action: Callable[[], None]) -> None:
        before = self.status
        action()                                # the current state decides, and may raise
        for listener in self._listeners:
            listener.on_event(event, before, self.status)


# ── Composition root ─────────────────────────────────────────────────────────

def run() -> list[str]:
    out: list[str] = []
    report = Report([AuditLog(out), ReferrerNotifier(out)])
    steps: list[tuple[str, Callable[[], None]]] = [
        ("edit", lambda: report.edit("No acute findings.")),
        ("sign_preliminary", report.sign_preliminary),
        ("edit", lambda: report.edit("No acute intracranial hemorrhage.")),
        ("sign_final", report.sign_final),
        ("edit", lambda: report.edit("No acute intracranial hemorrhage. Unchanged.")),
        ("addend", lambda: report.addend("Compared with prior CT: unchanged.")),
        ("sign_preliminary", report.sign_preliminary),
    ]
    for event, action in steps:
        try:
            action()
        except InvalidAction as error:
            out.append(f"reject  {event:<17}{error}")
    out.append(f"result  {report.status}: {report.body!r} + {len(report.addenda)} addendum")
    return out


if __name__ == "__main__":
    print("\n".join(run()))
