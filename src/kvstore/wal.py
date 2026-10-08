"""
Write-Ahead Log (WAL).

Every mutation is serialized to a single append-only file and fsynced to
disk before the caller is told the write succeeded. This is what makes
crash recovery possible: a `kill -9` between the WAL write and the
in-memory update always leaves the WAL as the source of truth.

Log format: one JSON object per line (simple, human-inspectable, easy to
debug — swap for a binary format later if throughput becomes a bottleneck).
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import asdict, dataclass


@dataclass
class LogEntry:
    op: str                 # "PUT" or "DELETE"
    key: str
    value: str | None = None  # utf-8 decoded value; None for DELETE


class WAL:
    def __init__(self, path: str):
        self.path = path
        self._lock = asyncio.Lock()
        self.entry_count = 0
        # create the file if it doesn't exist yet
        open(self.path, "a").close()
        self._fh = open(self.path, "a+", buffering=1)  # line-buffered

    async def append(self, entry: LogEntry) -> None:
        async with self._lock:
            line = json.dumps(asdict(entry))
            self._fh.write(line + "\n")
            self._fh.flush()
            os.fsync(self._fh.fileno())  # force to physical disk — the durability guarantee
            self.entry_count += 1

    def replay(self) -> list[LogEntry]:
        """Read every entry from disk, in order. Called once at startup."""
        entries: list[LogEntry] = []
        with open(self.path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                entries.append(LogEntry(**data))
        self.entry_count = len(entries)
        return entries

    def truncate(self) -> None:
        """Called right after a snapshot — the log before this point is now
        redundant, since its state is captured in the snapshot file."""
        self._fh.close()
        open(self.path, "w").close()
        self._fh = open(self.path, "a+", buffering=1)
        self.entry_count = 0

    def close(self) -> None:
        self._fh.close()
