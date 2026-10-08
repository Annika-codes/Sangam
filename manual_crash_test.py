"""
Real SIGKILL durability test — NOT a pytest. Run this manually to prove the
WAL survives an actual `kill -9`, not just a simulated close().

Usage:
    Terminal 1: python manual_crash_test.py write
                (writes 100k keys, then sleeps so you can kill -9 it)
    Terminal 2: kill -9 <pid-printed-by-terminal-1>
    Terminal 1: python manual_crash_test.py verify
                (loads the same WAL, confirms all keys survived)
"""

import asyncio
import sys
import os

sys.path.insert(0, "src")
from kvstore.wal import WAL
from kvstore.store import Store

WAL_PATH = "manual_test.wal"
N_KEYS = 100_000


async def write():
    if os.path.exists(WAL_PATH):
        os.remove(WAL_PATH)
    wal = WAL(WAL_PATH)
    store = Store(wal)
    for i in range(N_KEYS):
        await store.put(f"key{i}", f"val{i}".encode())
    print(f"wrote {N_KEYS} keys, pid={os.getpid()}")
    print("now run: kill -9", os.getpid())
    await asyncio.sleep(300)


def verify():
    wal = WAL(WAL_PATH)
    store = Store(wal)
    store.recover()
    missing = [i for i in range(N_KEYS) if store._data.get(f"key{i}") != f"val{i}".encode()]
    if missing:
        print(f"FAILED — {len(missing)} keys missing/corrupted, e.g. {missing[:5]}")
    else:
        print(f"PASSED — all {N_KEYS} keys recovered correctly after crash")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("write", "verify"):
        print(__doc__)
        sys.exit(1)
    if sys.argv[1] == "write":
        asyncio.run(write())
    else:
        verify()
