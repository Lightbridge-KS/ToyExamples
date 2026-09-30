"""The station's real job: take a weather reading every `period` seconds.

The fleet agent does not care what the job is. It only reads `is_alive`,
because "the process answers heartbeats" is not the same as "the work
is getting done".
"""
from __future__ import annotations

import asyncio
import random
import time


class Workload:
    """Stub sensor loop that records when it last produced a reading."""

    def __init__(self, period: float = 0.2, stale_after: float = 0.6) -> None:
        self.period, self.stale_after = period, stale_after
        self.last_reading: float | None = None
        self.temp_c: float | None = None
        self.frozen = False                       # flip to simulate a hung sensor

    async def run(self) -> None:
        """Take readings forever (unless frozen)."""
        while True:
            if not self.frozen:
                self.temp_c = round(random.uniform(18, 32), 1)
                self.last_reading = time.monotonic()
            await asyncio.sleep(self.period)

    @property
    def is_alive(self) -> bool:
        """True if a reading was taken recently."""
        return self.last_reading is not None and time.monotonic() - self.last_reading < self.stale_after
