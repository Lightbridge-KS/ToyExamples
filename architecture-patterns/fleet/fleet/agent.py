"""Fleet agent: runs on each station, beside the workload.

Its whole job: get a stable identity, register, then heartbeat forever,
healing itself from whatever the network or the control plane throws at it.
It holds a handle to the plane; the plane holds none back. Every call is
outbound, so a station behind NAT or a firewall needs no open port.
"""
from __future__ import annotations

import asyncio
import random
import uuid
from enum import Enum, auto
from pathlib import Path
from typing import Callable

from .control_plane import ControlPlane
from .workload import Workload


# ── Small parts ───────────────────────────────────────────────────────────────

def load_or_create_id(path: Path) -> str:
    """Stable identity: survive reboots so the plane sees one station, not two."""
    if path.exists():
        return path.read_text()
    station_id = str(uuid.uuid4())
    path.write_text(station_id)
    return station_id


class Outcome(Enum):
    """The only three things an HTTP reply can mean to the agent."""

    OK = auto()            # 200
    UNREGISTERED = auto()  # 401: the plane forgot us → register again
    FAILURE = auto()       # 5xx, timeout, anything else → back off


def to_outcome(status: int) -> Outcome:
    return {200: Outcome.OK, 401: Outcome.UNREGISTERED}.get(status, Outcome.FAILURE)


class Backoff:
    """Exponential backoff with full jitter, so a recovering plane isn't stampeded."""

    def __init__(self, base: float = 0.05, cap: float = 1.0) -> None:
        self.base, self.cap, self.attempt = base, cap, 0

    def next(self) -> float:
        window = min(self.cap, self.base * 2**self.attempt)
        self.attempt += 1
        return random.uniform(0, window)

    def reset(self) -> None:
        self.attempt = 0


# ── The agent ─────────────────────────────────────────────────────────────────

class StationAgent:
    """register → heartbeat loop → reconcile to whatever the plane asks for."""

    def __init__(
        self,
        name: str,
        firmware: str,
        plane: ControlPlane,
        workload: Workload,
        id_path: Path,
        interval: float = 0.3,
        say: Callable[[str], None] = print,
    ) -> None:
        self.name, self.firmware, self.interval = name, firmware, interval
        self.plane, self.workload, self.id_path = plane, workload, id_path
        self.backoff = Backoff()
        self.say = say
        self.station_id = ""

    async def run(self) -> None:
        self.station_id = load_or_create_id(self.id_path)
        await self._register_until_ok()
        while True:
            stats = {"workload_alive": self.workload.is_alive, "temp_c": self.workload.temp_c}
            body = {"station_id": self.station_id, "firmware": self.firmware, "stats": stats}
            status, reply = await self.plane.post("/heartbeat", body)
            match to_outcome(status):
                case Outcome.OK:
                    self.backoff.reset()
                    self._reconcile(reply)
                    await asyncio.sleep(self.interval)
                case Outcome.UNREGISTERED:
                    self._log("401 unknown station → re-register")
                    await self._register_until_ok()
                case Outcome.FAILURE:
                    await self._sleep_backoff(status)

    async def _register_until_ok(self) -> None:
        body = {"station_id": self.station_id, "name": self.name, "firmware": self.firmware}
        while True:
            status, reply = await self.plane.post("/register", body)
            if to_outcome(status) is Outcome.OK:
                break
            await self._sleep_backoff(status)
        self.backoff.reset()
        self._log(f"registered as {self.station_id[:8]}")
        self._reconcile(reply)

    def _reconcile(self, desired: dict) -> None:
        """Move actual state toward desired state; the next heartbeat reports it."""
        latest = desired["latest_firmware"]
        if latest != self.firmware:
            self._log(f"firmware {self.firmware} → {latest} (stub flash)")
            self.firmware = latest

    async def _sleep_backoff(self, status: int) -> None:
        delay = self.backoff.next()
        self._log(f"{status} → backoff {delay:.2f}s")
        await asyncio.sleep(delay)

    def _log(self, msg: str) -> None:
        self.say(f"  [{self.name}] {msg}")
