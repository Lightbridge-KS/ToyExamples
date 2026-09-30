"""Fleet architecture, minimal: weather stations phoning home to one control plane.

The pattern in one sentence: many agents each call OUT to a control plane
(register, then heartbeat forever); the plane keeps the registry, infers
health from silence, and hands back desired state in every reply.

Run (from the example folder):  uv run python -m fleet.demo
"""
from __future__ import annotations

import asyncio
import random
import tempfile
from pathlib import Path
from typing import Callable

from .agent import StationAgent
from .control_plane import ControlPlane
from .workload import Workload


def start_station(
    name: str, firmware: str, plane: ControlPlane, id_dir: Path, say: Callable[[str], None] = print
):
    """Composition root for one station: its workload and its fleet agent, side by side."""
    workload = Workload()
    agent = StationAgent(name, firmware, plane, workload, id_dir / f"{name}.id", say=say)
    tasks = [asyncio.create_task(workload.run()), asyncio.create_task(agent.run())]
    return workload, tasks


async def show(plane: ControlPlane, seconds: float = 1.5) -> None:
    """Let the fleet run for a while, then print what the operator sees."""
    await asyncio.sleep(seconds)
    print()
    plane.print_dashboard()


async def main() -> None:
    random.seed(7)
    plane = ControlPlane(latest_firmware="2.0.0")
    id_dir = Path(tempfile.mkdtemp())                # each station's "disk"

    print("── 1. Startup: every station registers, then heartbeats ──")
    stations = {n: start_station(n, "2.0.0", plane, id_dir) for n in ("rooftop-A", "hilltop-B", "valley-C")}
    await show(plane)

    print("\n── 2. valley-C loses power (nobody tells the plane) ──")
    for t in stations["valley-C"][1]:
        t.cancel()
    await show(plane)

    print("\n── 3. valley-C reboots: same id file → same row, no duplicate ──")
    stations["valley-C"] = start_station("valley-C", "2.0.0", plane, id_dir)
    await show(plane)

    print("\n── 4. hilltop-B's sensor hangs: the link stays up, the work stops ──")
    stations["hilltop-B"][0].frozen = True
    await show(plane)

    print("\n── 5. control plane restarts and loses its registry ──")
    plane.forget_all()
    await show(plane, seconds=0)                     # empty: the plane knows nobody
    await show(plane)                                # rebuilt from 401 → re-register

    print("\n── 6. operator publishes firmware 2.1.0 (a value on the plane, no push) ──")
    plane.latest_firmware = "2.1.0"
    await show(plane, seconds=0)                     # * = actual ≠ desired
    await show(plane)                                # converged on the next heartbeats

    for _, tasks in stations.values():
        for t in tasks:
            t.cancel()


if __name__ == "__main__":
    asyncio.run(main())
