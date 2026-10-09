# Report workflow: State, with Observer hooks (toy example)

*A radiology report moves from draft to preliminary to final to appended. Once final it is
locked, so a correction has to go in as an addendum. The same scenario is written twice: as
the GoF book draws it (96 lines of code, 10 classes) and in modern Python (78 lines, 4
classes, all plain data). The two files produce the same transcript.*

```sh
# from this folder
uv run classic.py              # the GoF shape
uv run modern.py               # the modern shape
uv run compare.py              # proof: both transcripts are identical
uv run modern.py --diagram     # the state machine, drawn from its own table
```

Read the two side by side: `code --diff classic.py modern.py`, or select both in VS Code's
Explorer and choose **Compare Selected**. UML for both shapes, and the generated state
diagram, are in [ARCHITECTURE.md](ARCHITECTURE.md).

## The idea

In the classic State pattern, the machine is spread across one class per state. To learn
"what can a final report do?", you open `Final` and see which methods it overrides. To learn
the whole machine, you open every class.

Here, a state's *behaviour* comes down to two things: which events it accepts, and where
each one leads. Both fit in a table, so the machine becomes **data**:

```
CLASSIC                                         MODERN
───────                                         ──────
class ReportState: every event raises           class Status(StrEnum): DRAFT, PRELIMINARY, ...
class Draft(ReportState):
    edit(): body = text                         TRANSITIONS = {
    sign_preliminary(): state = Preliminary()       (DRAFT, EDIT):             DRAFT,
    sign_final(): state = Final()                   (DRAFT, SIGN_PRELIMINARY): PRELIMINARY,
class Preliminary(ReportState): ...                 (DRAFT, SIGN_FINAL):       FINAL, ...
class Final(ReportState): addend() ...          }
class Appended(ReportState): addend() ...       fire(report, event): look up, apply, notify hooks
```

Once the machine is data, you can print it, test it exhaustively, and draw it:
`uv run modern.py --diagram` writes the Mermaid state diagram in
[ARCHITECTURE.md](ARCHITECTURE.md) from `TRANSITIONS`. The classic machine can only be
recovered by reading its code.

## Classic → modern

| Pattern | Classic (`classic.py`) | Modern (`modern.py`) | What does the work instead |
|---|---|---|---|
| **State** | `ReportState` base rejects every event; 4 subclasses override what they accept and swap `report.state` | `Status` + `TRANSITIONS[(status, event)]`; `fire()` looks up the move and applies the event's effect | `StrEnum`, a dict, `match` on the event |
| **Observer** | `ReportListener` ABC; `AuditLog`, `ReferrerNotifier`; `Report._handle()` notifies | `hooks=[audit(out), notify_referrer(out)]`, called with `(event, before, after)` | callables, as in [training-loop](../training-loop/README.md) |

**State is Strategy's twin.** Their class diagrams are the same shape: a context holding a
reference to an interface with interchangeable implementations. The difference is *who swaps
the implementation*. In Strategy the client picks one and it stays. In State the states swap
*themselves* (`report.state = Final()`) as events arrive. Compare the classic diagram in
[ARCHITECTURE.md](ARCHITECTURE.md) with [training-loop's](../training-loop/ARCHITECTURE.md).

## Why it works

- **The machine fits on one screen.** Seven rows of `TRANSITIONS` are the full answer to
  "what can happen when". A missing row means "rejected", and the table makes that visible.
- **It can audit itself.** Because the table is data, a few lines of code can prove that
  every status is reachable from `draft`, or list which statuses accept `edit`
  (`draft`, `preliminary`). This was checked against the toy's table. The classic machine
  has no data to query.
- **Hooks see before *and* after.** `Report` is frozen, so `fire()` still holds the old report
  when it calls the hooks. Classic listeners only get two status strings, because by the time
  they run the context has already changed.
- **The scenario is data too.** `STEPS` is a list of `(event, text)` pairs. The same machine
  can therefore replay an audit log, or run events that arrive as messages.

## The price

- **The table says *where*, not *what*.** The effects live in `fire()`'s `match` on the event,
  separate from the table. This works only because an event does the same thing in every
  state that accepts it (`edit` sets the body whether the report is draft or preliminary).
  Adding an event therefore means touching two places, the table and the `match`.
- **One `text` parameter for every event.** `sign_final` ignores it, and the type checker
  can't tell you that. Events as dataclasses (`Edit(text)`, `SignFinal()`), as in
  [undo-redo](../undo-redo/README.md), would type each payload.
- **Nothing forces the table to be complete or correct.** The table is easy to *test*, but no
  type checker checks it.

## When the classic still wins

- **Behaviour that really does differ per state.** If signing a preliminary report must also
  record "co-signed by attending" while signing a draft must not, the effect depends on
  `(status, event)`, not on the event alone. A `match` on the pair copes up to a point. When
  each state has lots of its own logic, as in a TCP connection or a game character, classes
  are the right home for it.
- **States with their own data.** A "retrying" state that tracks an attempt count and a
  deadline is easier to hold in a state object than as columns of the context.
- **Hierarchy.** Nested or parallel states (statecharts) outgrow both shapes, so you would
  reach for a library.

## Variants worth naming

- **`match (status, event)`.** One function with a case per accepted pair puts the
  transitions and their effects in one place. That fixes the first item under *The price*,
  but the machine can no longer draw itself.
- **Events as dataclasses.** `fire(report, Edit("..."))` types each payload, and turns the
  scenario into a command log you can replay.
- **Libraries.** `transitions` (Python) declares transitions as data:
  `{'trigger': ..., 'source': ..., 'dest': ...}`, with `on_enter_<state>` callbacks as hooks.
  XState (JS) does the same with statecharts.

## Where you meet it

- HL7 FHIR `DiagnosticReport.status`: `preliminary`, `final`, `amended`, `corrected`,
  `appended`, …: the status vocabulary this toy borrows.
- `django-fsm`: `@transition(field=state, source=..., target=...)` on model methods.
- AWS Step Functions: a machine written as JSON (Amazon States Language) and run by an
  engine.
- Order, ticket and PR lifecycles, wherever a status column has rules about what comes next.

## Exercises

1. **Cancel.** Add a `cancelled` status, reachable from `draft` and `preliminary` only. Count
   the places you edit in each file, then run `--diagram`.
2. **Audit the table.** Write a check that fails if any status is unreachable, or if a
   non-final status has no way forward. What would the same check look like for
   `classic.py`?
3. **Per-state effect.** Signing a preliminary report as final must record `cosigned=True`;
   signing a draft as final must not. Where does that go in each file? Does the table still
   hold the whole machine?
4. **Twins.** Put this toy's classic class diagram next to training-loop's. Find the one arrow
   that makes this one State rather than Strategy.
