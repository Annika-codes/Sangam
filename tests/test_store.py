import asyncio
import pytest

from kvstore.store import Store
from kvstore.wal import WAL


@pytest.mark.asyncio
async def test_put_get(tmp_path):
    wal = WAL(str(tmp_path / "test.wal"))
    store = Store(wal)

    await store.put("hello", b"world")
    assert await store.get("hello") == b"world"


@pytest.mark.asyncio
async def test_delete(tmp_path):
    wal = WAL(str(tmp_path / "test.wal"))
    store = Store(wal)

    await store.put("a", b"1")
    await store.delete("a")
    assert await store.get("a") is None


@pytest.mark.asyncio
async def test_concurrent_puts(tmp_path):
    """1000 concurrent writers; verify no data races, all keys land correctly."""
    wal = WAL(str(tmp_path / "test.wal"))
    store = Store(wal)

    async def writer(i: int):
        await store.put(f"key{i}", f"value{i}".encode())

    await asyncio.gather(*(writer(i) for i in range(1000)))

    for i in range(1000):
        assert await store.get(f"key{i}") == f"value{i}".encode()

    assert len(store) == 1000
