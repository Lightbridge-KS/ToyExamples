"""Control plane: the one place that knows the whole fleet.

It never calls a station. It only answers POSTs, and derives everything it
knows (who exists, who is online, who runs old firmware) from what stations
send it.
"""
from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field


@dataclass
class StationRecord:
    """What the control plane believes about one station."""

    station_id: str
    name: str
    firmware: str
    last_seen: float
    stats: dict = field(default_factory=dict)


class ControlPlane:
    """In-memory stand-in for a cloud endpoint: POST /register, POST /heartbeat."""

    def __init__(self, latest_firmware: str, failure_rate: float = 0.05) -> None:
        self.latest_firmware = latest_firmware    # desired state, set by an operator
        self.registry: dict[str, StationRecord] = {}
        self.failure_rate = failure_rate

    async def post(self, path: str, body: dict) -> tuple[int, dict]:
        """Simulate an HTTPS POST: return (status_code, json_body)."""
        await asyncio.sleep(0.01)                  # network latency
        if random.random() < self.failure_rate:
            return 503, {}                         # flaky network / overloaded plane
        match path:
            case "/register":
                return self._register(body)
            case "/heartbeat":
                return self._heartbeat(body)
        return 404, {}

    def _register(self, body: dict) -> tuple[int, dict]:
        """Upsert by station_id, so registering twice is harmless (idempotent)."""
        sid = body["station_id"]
        self.registry[sid] = StationRecord(sid, body["name"], body["firmware"], time.monotonic())
        return 200, self._desired_state()

    def _heartbeat(self, body: dict) -> tuple[int, dict]:
        """Refresh last_seen and stats, or 401 if this station is unknown."""
        record = self.registry.get(body["station_id"])
        if record is None:
            return 401, {"error": "unknown station"}   # → the station re-registers
        record.last_seen = time.monotonic()
        record.firmware = body["firmware"]
        record.stats = body["stats"]
        return 200, self._desired_state()

    def _desired_state(self) -> dict:
        """Instructions piggyback on every reply: the plane never pushes."""
        return {"latest_firmware": self.latest_firmware}

    # ── Operator view ─────────────────────────────────────────────────────────

    def forget_all(self) -> None:
        """Simulate a control-plane restart that loses the registry."""
        self.registry.clear()

    def dashboard(self, stale_after: float = 1.0) -> list[dict]:
        """One row per station. Online-ness is inferred from silence, never probed."""
        now = time.monotonic()
        return [
            {
                "name": r.name,
                "id": r.station_id[:8],
                "firmware": r.firmware + ("*" if r.firmware != self.latest_firmware else ""),
                "link": "online" if now - r.last_seen < stale_after else "STALE",
                "workload": {True: "alive", False: "DEAD"}.get(r.stats.get("workload_alive"), "?"),
                "temp_c": r.stats.get("temp_c", "-"),
            }
            for r in sorted(self.registry.values(), key=lambda r: r.name)
        ]

    def print_dashboard(self, stale_after: float = 1.0) -> None:
        """Print dashboard() as a table (* = firmware differs from desired)."""
        print(f"  {'NAME':<12}{'ID':<10}{'FIRMWARE':<10}{'LINK':<8}{'WORKLOAD':<10}TEMP°C")
        for row in self.dashboard(stale_after):
            print("  {name:<12}{id:<10}{firmware:<10}{link:<8}{workload:<10}{temp_c}".format(**row))
