"""
Snapshotting.

Replaying a huge WAL on every restart doesn't scale. A snapshot is a
point-in-time dump of the full in-memory state, tagged with the WAL
entry count at the moment it was taken (`wal_offset`), so recovery only
needs to replay WAL entries written AFTER the snapshot.

Writes are atomic: we write to a temp file, fsync it, then os.replace()
onto the real path. os.replace is atomic at the OS level, so a crash
mid-write can never leave a half-written, corrupted snapshot on disk.
"""

from __future__ import annotations

import os
import pickle


class SnapshotManager:
    def __init__(self, snapshot_path: str):
        self.snapshot_path = snapshot_path

    def save(self, data: dict[str, bytes], wal_offset: int) -> None:
        tmp_path = self.snapshot_path + ".tmp"
        with open(tmp_path, "wb") as f:
            pickle.dump({"data": data, "wal_offset": wal_offset}, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, self.snapshot_path)  # atomic rename

    def load(self) -> tuple[dict[str, bytes], int] | None:
        if not os.path.exists(self.snapshot_path):
            return None
        with open(self.snapshot_path, "rb") as f:
            obj = pickle.load(f)
        return obj["data"], obj["wal_offset"]


async def snapshot_loop(store, snapshot_mgr: SnapshotManager, interval_seconds: int = 60):
    """Background task: periodically snapshot the store and rotate the WAL.

    Run this with asyncio.create_task(snapshot_loop(store, mgr)) from your
    server's startup code.
    """
    import asyncio

    while True:
        await asyncio.sleep(interval_seconds)
        await store.snapshot()
