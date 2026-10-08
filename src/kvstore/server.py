"""
Server entrypoint.

NOTE: This is a minimal line-protocol TCP server (GET/PUT/DELETE as plain
text commands) so the engine is runnable and testable end-to-end right now.
Step 1d of the build plan replaces this with a proper async gRPC server
(see proto/kvstore.proto) — swap it in once that's wired up without
touching store.py, wal.py, or snapshot.py at all.

Usage:
    python -m kvstore.server --port 8001 --data-dir ./data
"""

from __future__ import annotations

import argparse
import asyncio
import os

from kvstore.store import Store
from kvstore.wal import WAL
from kvstore.snapshot import SnapshotManager, snapshot_loop


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, store: Store):
    while True:
        line = await reader.readline()
        if not line:
            break
        parts = line.decode().strip().split(" ", 2)
        if not parts or parts[0] == "":
            continue

        cmd = parts[0].upper()
        try:
            if cmd == "GET" and len(parts) == 2:
                value = await store.get(parts[1])
                resp = value.decode() if value is not None else "NIL"
            elif cmd == "PUT" and len(parts) == 3:
                await store.put(parts[1], parts[2].encode())
                resp = "OK"
            elif cmd == "DELETE" and len(parts) == 2:
                await store.delete(parts[1])
                resp = "OK"
            else:
                resp = "ERR unknown command"
        except Exception as e:  # noqa: BLE001 — surface errors to the client, don't crash the server
            resp = f"ERR {e}"

        writer.write((resp + "\n").encode())
        await writer.drain()

    writer.close()
    await writer.wait_closed()


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--data-dir", type=str, default="./data")
    parser.add_argument("--snapshot-interval", type=int, default=60)
    args = parser.parse_args()

    os.makedirs(args.data_dir, exist_ok=True)
    wal_path = os.path.join(args.data_dir, f"node-{args.port}.wal")
    snap_path = os.path.join(args.data_dir, f"node-{args.port}.snap")

    wal = WAL(wal_path)
    snapshot_mgr = SnapshotManager(snap_path)
    store = Store(wal, snapshot_mgr)

    print(f"[node:{args.port}] recovering from disk...")
    store.recover()
    print(f"[node:{args.port}] recovered {len(store)} keys")

    asyncio.create_task(snapshot_loop(store, snapshot_mgr, args.snapshot_interval))

    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, store), "127.0.0.1", args.port
    )
    print(f"[node:{args.port}] listening on 127.0.0.1:{args.port}")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
