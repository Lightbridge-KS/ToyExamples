#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Report workflow, MODERN shape: the state machine as data, with hooks for side effects.

    State    -> a StrEnum of statuses plus a TRANSITIONS table: (status, event) -> next status.
                Per-state behaviour is "which events does the table accept", so it is data too.
    Observer -> hooks: plain callables that receive the event and the report before and after.

The table is data, so the machine can draw itself:  uv run modern.py --diagram

Open next to classic.py: the scenario is the same and so is the transcript.

Run:  uv run modern.py
"""
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from enum import StrEnum, auto


class InvalidAction(Exception):
    pass


class Status(StrEnum):
    DRAFT = auto()
    PRELIMINARY = auto()
    FINAL = auto()
    APPENDED = auto()


class Event(StrEnum):
    EDIT = auto()
    SIGN_PRELIMINARY = auto()
    SIGN_FINAL = auto()
    ADDEND = auto()


# ── State -> the whole machine as a table. A missing row means "rejected" ────

TRANSITIONS: dict[tuple[Status, Event], Status] = {
    (Status.DRAFT, Event.EDIT): Status.DRAFT,
    (Status.DRAFT, Event.SIGN_PRELIMINARY): Status.PRELIMINARY,
    (Status.DRAFT, Event.SIGN_FINAL): Status.FINAL,
    (Status.PRELIMINARY, Event.EDIT): Status.PRELIMINARY,
    (Status.PRELIMINARY, Event.SIGN_FINAL): Status.FINAL,
    (Status.FINAL, Event.ADDEND): Status.APPENDED,
    (Status.APPENDED, Event.ADDEND): Status.APPENDED,
}


@dataclass(frozen=True)
class Report:
    status: Status = Status.DRAFT
    body: str = ""
    addenda: tuple[str, ...] = ()


type Hook = Callable[[Event, Report, Report], None]     # (event, before, after) -> None


def fire(report: Report, event: Event, text: str = "", *, hooks: Sequence[Hook] = ()) -> Report:
    """Apply one event: the table says whether and where to move, the match says what changes."""
    if (report.status, event) not in TRANSITIONS:
        raise InvalidAction(f"cannot {event} when {report.status}")
    after = replace(report, status=TRANSITIONS[report.status, event])
    match event:                                # an event's effect doesn't depend on the status
        case Event.EDIT:
            after = replace(after, body=text)
        case Event.ADDEND:
            after = replace(after, addenda=(*report.addenda, text))
    for hook in hooks:
        hook(event, report, after)              # the old report still exists, so hooks see both
    return after


def to_mermaid() -> str:
    """Render TRANSITIONS as a Mermaid state diagram."""
    lines = ["stateDiagram-v2", f"    [*] --> {Status.DRAFT}"]
    lines += [f"    {source} --> {target} : {event}" for (source, event), target in TRANSITIONS.items()]
    return "\n".join(lines)


# ── Observer -> hooks are just functions ─────────────────────────────────────

def audit(out: list[str]) -> Hook:
    def hook(event: Event, before: Report, after: Report) -> None:
        out.append(f"audit   {event:<17}{before.status:<12}→ {after.status}")
    return hook


def notify_referrer(out: list[str]) -> Hook:
    def hook(event: Event, before: Report, after: Report) -> None:
        if after.status is Status.FINAL and before.status is not Status.FINAL:
            out.append("notify  referring physician: report is final")
    return hook


# ── Composition root: the scenario is a list of events, also data ────────────

STEPS = [
    (Event.EDIT, "No acute findings."),
    (Event.SIGN_PRELIMINARY, ""),
    (Event.EDIT, "No acute intracranial hemorrhage."),
    (Event.SIGN_FINAL, ""),
    (Event.EDIT, "No acute intracranial hemorrhage. Unchanged."),
    (Event.ADDEND, "Compared with prior CT: unchanged."),
    (Event.SIGN_PRELIMINARY, ""),
]


def run() -> list[str]:
    out: list[str] = []
    hooks = [audit(out), notify_referrer(out)]
    report = Report()
    for event, text in STEPS:
        try:
            report = fire(report, event, text, hooks=hooks)
        except InvalidAction as error:
            out.append(f"reject  {event:<17}{error}")
    out.append(f"result  {report.status}: {report.body!r} + {len(report.addenda)} addendum")
    return out


if __name__ == "__main__":
    print(to_mermaid() if "--diagram" in sys.argv[1:] else "\n".join(run()))
