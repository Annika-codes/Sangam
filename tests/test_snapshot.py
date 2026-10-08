import pytest

from kvstore.wal import WAL
from kvstore.store import Store
from kvstore.snapshot import SnapshotManager


@pytest.mark.asyncio
async def test_snapshot_save_and_load(tmp_path):
    snap_path = str(tmp_path / "test.snap")
    mgr = SnapshotManager(snap_path)

    data = {"a": b"1", "b": b"2"}
    mgr.save(data, wal_offset=2)

    loaded_data, offset = mgr.load()
    assert loaded_data == data
    assert offset == 2


def test_load_returns_none_when_missing(tmp_path):
    mgr = SnapshotManager(str(tmp_path / "nonexistent.snap"))
    assert mgr.load() is None


@pytest.mark.asyncio
async def test_snapshot_then_partial_replay(tmp_path):
    """The real scenario: snapshot mid-way, write more, crash, recover.
    recover() should only replay WAL entries AFTER the snapshot offset,
    not the full history."""
    wal_path = str(tmp_path / "test.wal")
    snap_path = str(tmp_path / "test.snap")

    wal = WAL(wal_path)
    snap_mgr = SnapshotManager(snap_path)
    store = Store(wal, snap_mgr)

    # phase 1: write 500 keys, then snapshot
    for i in range(500):
        await store.put(f"key{i}", f"val{i}".encode())
    await store.snapshot()  # this also truncates the WAL

    # phase 2: write 200 more keys AFTER the snapshot
    for i in range(500, 700):
        await store.put(f"key{i}", f"val{i}".encode())

    # simulate crash + restart
    wal.close()
    wal2 = WAL(wal_path)
    store2 = Store(wal2, snap_mgr)
    store2.recover()

    # all 700 keys should be present — 500 from snapshot, 200 from WAL replay
    for i in range(700):
        assert await store2.get(f"key{i}") == f"val{i}".encode()

    # the WAL itself should only contain the post-snapshot entries
    assert wal2.entry_count == 200
