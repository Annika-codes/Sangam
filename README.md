<p align="center">
  <img src="banner.svg" alt="SANGAM: distributed key-value store, written from scratch" width="100%">
</p>

<p align="center">
  <img alt="python" src="https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white">
  <img alt="tests" src="https://img.shields.io/badge/tests-9%20passing-2ea44f?style=flat-square">
  <img alt="status" src="https://img.shields.io/badge/phase%201-complete-fbbf24?style=flat-square">
  <img alt="license" src="https://img.shields.io/badge/license-MIT-blue?style=flat-square">
</p>

<p align="center">
  <a href="#why-this-exists">Why</a> ·
  <a href="#how-a-write-survives-a-crash">Durability</a> ·
  <a href="#benchmarks">Benchmarks</a> ·
  <a href="#design-decisions">Design</a> ·
  <a href="#run-it">Run it</a> ·
  <a href="#roadmap">Roadmap</a>
</p>

---

## Why this exists

Most "distributed key-value store" projects wrap Redis or import a consensus library. Sangam is built the other way round: every layer is written by hand, starting from a single crash-safe node and growing outward to replication and sharding, so each piece can be tested against real failures before the next is added.

**Phase 1 (this repo today)** is the single-node storage engine: an in-memory store with a write-ahead log and atomic snapshots that recovers its full state after a hard process kill.

**Phase 2 (in progress)** makes it distributed: Raft leader election and log replication, then consistent-hash sharding. The long-term goal is to use it as a shared prefix cache for an on-device LLM inference engine.

> *Sangam* is Sanskrit for a confluence, the point where separate streams meet and become one. That is the job of a consensus protocol.

## How a write survives a crash

```
 client            Store                    WAL (disk)             memory
   │  PUT k v        │                          │                     │
   ├────────────────▶│  1. append entry         │                     │
   │                 ├─────────────────────────▶│                     │
   │                 │  2. fsync (force to disk)│                     │
   │                 │◀─────────────────────────┤                     │
   │                 │  3. only now: apply      │                     │
   │                 ├──────────────────────────────────────────────▶ │
   │◀────────────────┤  4. acknowledge          │                     │
```

The order is the whole guarantee. If the process dies between steps 2 and 3, the entry is already on disk and `recover()` replays it on restart. If memory were updated first, a crash would silently lose the write.

**Recovery** loads the latest snapshot, then replays only the WAL entries written after it:

```
 snapshot.snap  ──▶  full state at time T
 node.wal       ──▶  only entries since T      ──▶  state restored
```

## Benchmarks

Measured with [`benchmark.py`](benchmark.py) on a Windows laptop, 20,000 keys, `fsync` on every write.

| Metric | Result |
|:--|--:|
| Reads (in-memory) | **~818,000 / s** |
| Durable writes (fsync each) | **~367 / s** |
| Recovery, full WAL replay | 85.8 ms |
| Recovery, snapshot + 500 new entries | **22.8 ms** (3.8x faster) |
| WAL entries replayed after a snapshot | **500** instead of 20,500 (97.6% fewer) |

The write figure is low on purpose: every write waits for the disk to confirm it, which is the price of the durability guarantee. The standard fix is group commit (batching several writes into one `fsync`), which is on the roadmap. Numbers vary by machine, so run the script yourself:

```
python benchmark.py
```

## Design decisions

| Decision | Why |
|:--|:--|
| **WAL write and `fsync` before the in-memory update** | A crash at any point leaves the log as the source of truth. |
| **Snapshots written to a temp file, then `os.replace`** | The rename is atomic, so a crash mid-write can never leave a half-written snapshot. |
| **WAL truncated right after each snapshot** | The log on disk only ever holds entries since the last snapshot, so restart time tracks recent writes, not total history. |
| **`asyncio.Lock` around every operation** | Tasks can interleave at `await` points, including the one inside the WAL write. |

**A bug the tests caught:** `recover()` originally skipped WAL entries by the snapshot's offset, but the WAL had already been truncated at that offset, so it skipped them twice and lost data. The snapshot test caught it, and the fix removed the redundant slice and documented the invariant above.

## Run it

```bash
git clone https://github.com/<your-username>/sangam.git
cd sangam
pip install -r requirements.txt
```

**Tests** (9 cases: concurrent writers, crash recovery, snapshot and WAL consistency)

```bash
# macOS / Linux
PYTHONPATH=src pytest tests/ -v

# Windows PowerShell
$env:PYTHONPATH="src"; pytest tests/ -v
```

**Start a node** (a plain-text TCP server, to be replaced by gRPC)

```bash
python -m kvstore.server --port 8001
```

Then connect and send `PUT key value`, `GET key` or `DELETE key`, one per line. Stop the server, start it again, and your keys are still there.

**Crash test.** Run `python manual_crash_test.py write`, force-kill the process it prints the PID of, then run `python manual_crash_test.py verify` to check that every key survived.

## Project layout

```
sangam/
├── banner.svg
├── benchmark.py
├── manual_crash_test.py
├── src/kvstore/
│   ├── store.py        in-memory store, recovery
│   ├── wal.py          write-ahead log
│   ├── snapshot.py     atomic snapshots, snapshot loop
│   └── server.py       async TCP server
├── tests/
│   ├── test_store.py
│   ├── test_wal.py
│   └── test_snapshot.py
└── requirements.txt
```

## Roadmap

- [x] In-memory store with `asyncio`-safe access
- [x] Write-ahead log with `fsync` durability
- [x] Atomic snapshots with WAL truncation
- [x] Crash-recovery tests and benchmark script
- [ ] gRPC server (replaces the TCP stub)
- [ ] Raft leader election
- [ ] Raft log replication
- [ ] Consistent-hash sharding with virtual nodes
- [ ] Multi-node fault injection: kill a leader mid-write, partition the network
- [ ] Group commit to raise durable write throughput
- [ ] Wire in as a distributed prefix cache for an on-device LLM inference engine

## License

MIT. See [LICENSE](LICENSE).
