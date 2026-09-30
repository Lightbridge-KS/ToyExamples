#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Hub-and-spoke, minimal: a smart-home hub and three devices.

The pattern in one sentence: every spoke talks ONLY to the hub, so the hub
is the single place where coordination, routing and the address book live.

Run:  uv run hub_and_spoke.py
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ── Spokes ────────────────────────────────────────────────────────────────────
# A spoke knows one thing about the outside world: its hub. It has no list of
# other devices, so spoke-to-spoke talk is impossible by construction, not by
# policy. That is the load-bearing property of the pattern.

@dataclass
class Spoke:
    name: str
    hub: "Hub"
    state: str = "unknown"

    def __post_init__(self) -> None:
        self.hub.register(self)          # the hub owns the address book

    def apply(self, command: str) -> str:
        """Hub → spoke. Reconcile to the command, return a receipt."""
        self.state = command
        return f"{self.name}: now {self.state}"

    def report(self, event: str) -> None:
        """Spoke → hub. The spoke emits; it never decides who cares."""
        self.hub.on_event(self, event)


# ── Hub ───────────────────────────────────────────────────────────────────────
# All coordination lives here: the registry (who exists), the scenes (desired
# state), and routing (which event should make which spoke do what).

@dataclass
class Hub:
    spokes: dict[str, Spoke] = field(default_factory=dict)
    scenes: dict[str, dict[str, str]] = field(default_factory=dict)
    routes: dict[str, tuple[str, str]] = field(default_factory=dict)

    def register(self, spoke: Spoke) -> None:
        self.spokes[spoke.name] = spoke

    def apply_scene(self, scene: str) -> list[str]:
        """Fan-out: one hub call becomes N spoke calls. Hub initiates, spokes obey."""
        receipts = [self.spokes[n].apply(cmd) for n, cmd in self.scenes[scene].items()]
        return receipts

    def on_event(self, source: Spoke, event: str) -> None:
        """Fan-in + route: a spoke's event reaches another spoke only via the hub."""
        if event not in self.routes:
            print(f"  hub: {source.name} said '{event}' — no route, ignored")
            return
        target, cmd = self.routes[event]
        print(f"  hub: {source.name} said '{event}' → {self.spokes[target].apply(cmd)}")


# ── Demo ──────────────────────────────────────────────────────────────────────

def main() -> None:
    hub = Hub(
        scenes={
            "movie":   {"light": "dim 20%", "blinds": "closed", "thermostat": "21°C"},
            "morning": {"light": "on",      "blinds": "open",   "thermostat": "23°C"},
        },
        routes={"motion": ("light", "on")},   # event → (target spoke, command)
    )
    light, blinds, sensor = (Spoke(n, hub) for n in ("light", "blinds", "sensor"))
    thermostat = Spoke("thermostat", hub)

    print("1. Hub → spokes (fan-out): apply scene 'movie'")
    for r in hub.apply_scene("movie"):
        print("  ", r)

    print("\n2. Spoke → hub → spoke (routed): sensor sees motion")
    sensor.report("motion")

    print("\n3. Unknown event: the hub decides, not the spoke")
    blinds.report("wind gust")

    print("\n4. Wiring cost for N devices — why the star wins as N grows")
    for n in (3, 5, 10, 50):
        print(f"   N={n:>2}  hub-and-spoke: {n:>4} links   mesh: {n * (n - 1) // 2:>5} links")

    print("\n5. The price: no hub, no coordination (single point of failure)")
    try:
        Spoke("orphan", hub=None)  # type: ignore[arg-type]
    except AttributeError:
        print("   orphan spoke cannot even register — nothing to register with")


if __name__ == "__main__":
    main()
