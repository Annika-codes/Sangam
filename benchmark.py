import asyncio, sys, time, tempfile
sys.path.insert(0, "src")
from kvstore.wal import WAL
from kvstore.store import Store
from kvstore.snapshot import SnapshotManager

N = 20000

async def main():
    d = tempfile.mkdtemp()
    wp, sp = f"{d}/a.wal", f"{d}/a.snap"
    wal = WAL(wp); snap = SnapshotManager(sp); store = Store(wal, snap)

    t = time.perf_counter()
    for i in range(N):
        await store.put(f"key{i}", f"val{i}".encode())
    dt = time.perf_counter() - t
    print(f"durable writes (fsync each): {N} in {dt:.2f}s = {N/dt:,.0f} writes/s")

    t = time.perf_counter()
    for i in range(N):
        await store.get(f"key{i}")
    dt = time.perf_counter() - t
    print(f"reads: {N/dt:,.0f} reads/s")

    wal.close()
    wal2 = WAL(wp); s2 = Store(wal2, snap)
    t = time.perf_counter(); s2.recover(); full = time.perf_counter() - t
    print(f"full WAL replay recovery: {len(s2)} keys in {full*1000:.1f} ms")
    wal2.close()

    wal3 = WAL(wp); s3 = Store(wal3, snap); s3.recover()
    await s3.snapshot()
    for i in range(N, N+500):
        await s3.put(f"key{i}", f"val{i}".encode())
    wal3.close()
    wal4 = WAL(wp); s4 = Store(wal4, snap)
    t = time.perf_counter(); s4.recover(); snapt = time.perf_counter() - t
    print(f"snapshot+500 replay recovery: {len(s4)} keys in {snapt*1000:.1f} ms ({full/snapt:.1f}x faster)")
    print(f"WAL entries replayed: {wal4.entry_count} instead of {N+500}")

asyncio.run(main())
