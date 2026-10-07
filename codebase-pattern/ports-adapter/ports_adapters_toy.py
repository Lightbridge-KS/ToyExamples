"""
Ports & Adapters (Hexagonal Architecture) — toy example.

Use case: "complete a task" -> mark it done, persist it, notify someone.

    CORE      : Task entity + CompleteTask use case + the PORTS it owns
    ADAPTERS  : plug technology into those ports (memory, JSON file, console, spy)
    MAIN      : composition root — the only place that knows both sides
"""
from __future__ import annotations

import json
import tempfile
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from pathlib import Path


# ═════════════════════════════ CORE (the hexagon) ═════════════════════════════
# Rule: nothing in this section imports or mentions a technology.

@dataclass
class Task:
    id: int
    title: str
    done: bool = False

    def complete(self) -> None:
        if self.done:                       # a business rule lives in the core
            raise ValueError(f"Task {self.id} is already done")
        self.done = True


# ── Driven (secondary) ports: what the core NEEDS from the outside world ──
class ITaskRepository(ABC):
    @abstractmethod
    def get(self, task_id: int) -> Task: ...

    @abstractmethod
    def save(self, task: Task) -> None: ...


class INotifier(ABC):
    @abstractmethod
    def notify(self, message: str) -> None: ...


# ── Driving (primary) port: what the core OFFERS to the outside world ──
# Here the port is simply the public method `execute`. No ABC: there is
# only one implementation, so an interface would be a pass-through.
class CompleteTask:
    def __init__(self, repo: ITaskRepository, notifier: INotifier) -> None:
        self._repo = repo
        self._notifier = notifier

    def execute(self, task_id: int) -> None:
        task = self._repo.get(task_id)
        task.complete()
        self._repo.save(task)
        self._notifier.notify(f"Task '{task.title}' completed")


# ═════════════════════════════ DRIVEN ADAPTERS ═════════════════════════════
# Each one translates the core's language (Task) <-> a technology.

class InMemoryTaskRepository(ITaskRepository):
    def __init__(self, tasks: list[Task]) -> None:
        self._tasks = {t.id: t for t in tasks}

    def get(self, task_id: int) -> Task:
        return self._tasks[task_id]

    def save(self, task: Task) -> None:
        self._tasks[task.id] = task


class JsonFileTaskRepository(ITaskRepository):
    """Second adapter for the same port -> proof the seam is real."""
    def __init__(self, path: Path) -> None:
        self._path = path

    def get(self, task_id: int) -> Task:
        rows = json.loads(self._path.read_text())
        return Task(**rows[str(task_id)])          # JSON dict -> domain object

    def save(self, task: Task) -> None:
        rows = json.loads(self._path.read_text())
        rows[str(task.id)] = asdict(task)          # domain object -> JSON dict
        self._path.write_text(json.dumps(rows, indent=2))


class ConsoleNotifier(INotifier):
    def notify(self, message: str) -> None:
        print(f"[console] {message}")


class SpyNotifier(INotifier):
    """Test adapter: records instead of sending."""
    def __init__(self) -> None:
        self.sent: list[str] = []

    def notify(self, message: str) -> None:
        self.sent.append(message)


# ═════════════════════════════ DRIVING ADAPTER ═════════════════════════════
# Translates a CLI string into a call on the core's driving port.

def cli(command: str, use_case: CompleteTask) -> None:
    verb, arg = command.split()                    # e.g. "done 1"
    if verb != "done":
        raise SystemExit(f"unknown command: {verb}")
    use_case.execute(int(arg))


# ═════════════════════════ COMPOSITION ROOT (main) ═════════════════════════

def demo_production() -> None:
    print("── production wiring: JSON file + console ──")
    path = Path(tempfile.mkdtemp()) / "tasks.json"
    path.write_text(json.dumps({"1": {"id": 1, "title": "Write report", "done": False}}))

    use_case = CompleteTask(JsonFileTaskRepository(path), ConsoleNotifier())
    cli("done 1", use_case)
    print(path.read_text())


def demo_test() -> None:
    print("── test wiring: in-memory + spy (no disk, no I/O) ──")
    repo = InMemoryTaskRepository([Task(1, "Write report")])
    spy = SpyNotifier()

    CompleteTask(repo, spy).execute(1)             # a test is just another driver

    assert repo.get(1).done is True
    assert spy.sent == ["Task 'Write report' completed"]
    print("assertions passed:", spy.sent)


if __name__ == "__main__":
    demo_production()
    demo_test()
