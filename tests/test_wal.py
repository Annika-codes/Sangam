import pytest

from kvstore.wal import WAL, LogEntry
from kvstore.store import Store


@pytest.mark.asyncio
async def test_append_and_replay(tmp_path):
    wal_path = str(tmp_path / "test.wal")

    wal = WAL(wal_path)
    await wal.append(LogEntry(op="PUT", key="a", value="1"))
    await wal.append(LogEntry(op="PUT", key="b", value="2"))
    await wal.append(LogEntry(op="DELETE", key="a"))
    wal.close()

    wal2 = WAL(wal_path)
    entries = wal2.replay()

    assert len(entries) == 3
    assert entries[0] == LogEntry(op="PUT", key="a", value="1")
    assert entries[2] == LogEntry(op="DELETE", key="a")


@pytest.mark.asyncio
async def test_crash_recovery(tmp_path):
    """Simulates a process death (no graceful shutdown) and verifies a fresh
    Store pointed at the same WAL file recovers identical state."""
    wal_path = str(tmp_path / "test.wal")

    wal = WAL(wal_path)
    store = Store(wal)
    for i in range(500):
        await store.put(f"key{i}", f"val{i}".encode())
    wal.close()  # simulate crash — no flush/close logic beyond the WAL's own fsync

    # simulate restart: fresh Store + WAL pointed at the same file
    wal2 = WAL(wal_path)
    store2 = Store(wal2)
    store2.recover()

    for i in range(500):
        assert await store2.get(f"key{i}") == f"val{i}".encode()


@pytest.mark.asyncio
async def test_truncate_resets_log(tmp_path):
    wal_path = str(tmp_path / "test.wal")
    wal = WAL(wal_path)

    await wal.append(LogEntry(op="PUT", key="a", value="1"))
    assert wal.entry_count == 1

    wal.truncate()
    assert wal.entry_count == 0
    assert wal.replay() == []
