"""
Core in-memory key-value store.

Durability model:
    1. Every PUT/DELETE is appended to the Write-Ahead Log (WAL) and fsynced
       to disk BEFORE the in-memory dict is mutated.
    2. On startup, recover() loads the latest snapshot (if any) and replays
       only the WAL entries written after that snapshot.

This ordering is the entire correctness guarantee of the engine: if the
process dies between the WAL write and the in-memory update, the WAL already
has the entry and recover() will replay it correctly on restart.
"""

from __future__ import annotations

import asyncio

from kvstore.wal import WAL, LogEntry
from kvstore.snapshot import SnapshotManager


class Store:
    def __init__(self, wal: WAL, snapshot_mgr: SnapshotManager | None = None):
        self._data: dict[str, bytes] = {}
        self._lock = asyncio.Lock()
        self._wal = wal
        self._snapshot_mgr = snapshot_mgr

    # ------------------------------------------------------------------ #
    # Read path
    # ------------------------------------------------------------------ #
    async def get(self, key: str) -> bytes | None:
        async with self._lock:
            return self._data.get(key)

    # ------------------------------------------------------------------ #
    # Write path
    # ------------------------------------------------------------------ #
    async def put(self, key: str, value: bytes) -> None:
        async with self._lock:
            await self._wal.append(LogEntry(op="PUT", key=key, value=value.decode("utf-8")))
            self._data[key] = value

    async def delete(self, key: str) -> None:
        async with self._lock:
            await self._wal.append(LogEntry(op="DELETE", key=key))
            self._data.pop(key, None)

    # ------------------------------------------------------------------ #
    # Recovery
    # ------------------------------------------------------------------ #
    def recover(self) -> None:
        """Called once at startup, before the store serves any requests.

        Loads the latest snapshot (if one exists), then replays every entry
        in the CURRENT WAL file. This relies on an invariant: snapshot()
        always truncates the WAL immediately after saving, so the WAL file
        on disk only ever contains entries written SINCE the last snapshot.
        That's what keeps restart time proportional to recent writes rather
        than full history, without needing to slice by offset here.
        """
        if self._snapshot_mgr is not None:
            snap = self._snapshot_mgr.load()
            if snap is not None:
                data, _wal_offset_at_snapshot = snap
                self._data = data

        entries = self._wal.replay()
        for entry in entries:
            if entry.op == "PUT":
                assert entry.value is not None
                self._data[entry.key] = entry.value.encode("utf-8")
            elif entry.op == "DELETE":
                self._data.pop(entry.key, None)

    # ------------------------------------------------------------------ #
    # Snapshot trigger (called by the background snapshot loop)
    # ------------------------------------------------------------------ #
    async def snapshot(self) -> None:
        if self._snapshot_mgr is None:
            return
        async with self._lock:
            self._snapshot_mgr.save(self._data.copy(), self._wal.entry_count)
            self._wal.truncate()

    def __len__(self) -> int:
        return len(self._data)
