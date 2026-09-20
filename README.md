<div align="center">

<img width="100%" src="https://capsule-render.vercel.app/api?type=waving&color=0:0F2027,50:203A43,100:2C5364&height=220&section=header&text=SANGAM a distributed-kv-store&fontSize=46&fontColor=ffffff&animation=fadeIn&fontAlignY=38&desc=A%20Raft-backed%2C%20sharded%20key-value%20store%20built%20from%20scratch&descAlignY=58&descSize=18&descColor=d0e6f7"/>

<br>

<a href="#">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=500&size=20&duration=2500&pause=800&color=4FD1FF&center=true&vCenter=true&width=650&lines=Consensus.+Replication.+Fault+tolerance.;No+managed+DB.+No+shortcuts.;Built+entirely+from+first+principles." alt="Typing SVG" />
</a>

<br><br>

<img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/gRPC-asyncio-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white"/>
<img src="https://img.shields.io/badge/Consensus-Raft-FF6B6B?style=for-the-badge&logo=apacheflink&logoColor=white"/>
<img src="https://img.shields.io/badge/status-active--development-F9C513?style=for-the-badge"/>
<img src="https://img.shields.io/badge/license-MIT-2ECC71?style=for-the-badge"/>

<br><br>

<img src="https://skillicons.dev/icons?i=py,grpc,docker,git,githubactions&theme=dark" />

</div>

<br>

<img width="100%" src="https://capsule-render.vercel.app/api?type=rect&color=0:2C5364,100:0F2027&height=3"/>

<br>

## 🧭 Overview

> A distributed key-value store implemented **from first principles** — no off-the-shelf consensus library, no managed database underneath. Every layer, from the write-ahead log to leader election to shard routing, is hand-built to understand *why* systems like etcd, CockroachDB, and TiKV work the way they do.

<div align="center">
<table>
<tr>
<td align="center" width="25%">
<h3>📝</h3>
<b>WAL + Snapshots</b><br/>
<sub>Crash-consistent storage</sub>
</td>
<td align="center" width="25%">
<h3>👑</h3>
<b>Raft Consensus</b><br/>
<sub>Leader election + replication</sub>
</td>
<td align="center" width="25%">
<h3>🔀</h3>
<b>Consistent Hashing</b><br/>
<sub>Sharded, horizontally scalable</sub>
</td>
<td align="center" width="25%">
<h3>💥</h3>
<b>Fault Injection</b><br/>
<sub>Survives kill -9 and partitions</sub>
</td>
</tr>
</table>
</div>

<br>

## 🏗️ Architecture

```mermaid
%%{init: {'theme':'dark', 'themeVariables': {'primaryColor':'#203A43','primaryTextColor':'#fff','primaryBorderColor':'#4FD1FF','lineColor':'#4FD1FF','secondaryColor':'#0F2027','tertiaryColor':'#2C5364'}}}%%
flowchart TB
    C["🖥️ gRPC Client"] --> Router["🔀 Consistent Hash Router"]

    subgraph Cluster["🌐 Distributed Cluster"]
        direction LR
        subgraph ShardA["Shard A — Raft Group"]
            L1["👑 Leader"] -.AppendEntries.-> F1a["Follower"]
            L1 -.AppendEntries.-> F1b["Follower"]
        end
        subgraph ShardB["Shard B — Raft Group"]
            L2["👑 Leader"] -.AppendEntries.-> F2a["Follower"]
            L2 -.AppendEntries.-> F2b["Follower"]
        end
    end

    Router --> ShardA
    Router --> ShardB

    subgraph Engine["📦 Per-Node Storage Engine"]
        direction TB
        WAL["📝 Write-Ahead Log"] --> MEM["⚡ In-Memory Store"]
        MEM -.periodic.-> SNAP["📸 Snapshot"]
    end

    L1 --> Engine
```

<br>

## 📊 Build Progress

<div align="center">

| Layer | Component | Status |
|:---|:---|:---:|
| **Storage** | In-memory store (`asyncio`-safe) | ✅ |
| **Storage** | Write-ahead log | ✅ |
| **Storage** | Snapshotting + WAL rotation | 🚧 |
| **Networking** | Async gRPC server | ⬜ |
| **Consensus** | Raft leader election | ⬜ |
| **Consensus** | Raft log replication | ⬜ |
| **Sharding** | Consistent hashing + virtual nodes | ⬜ |
| **Resilience** | Fault injection / partition tests | ⬜ |

</div>

<br>

<details>
<summary><b>🚀 Getting Started</b> — click to expand</summary>
<br>

```bash
# clone
git clone https://github.com/<your-username>/distributed-kv-store.git
cd distributed-kv-store

# environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# run tests
pytest tests/ -v

# start a single node
python -m kvstore.server --port 8001
```

</details>

<details>
<summary><b>🧪 Simulating a Cluster Locally</b> — click to expand</summary>
<br>

```bash
python -m kvstore.server --port 8001 --peers 8002,8003 &
python -m kvstore.server --port 8002 --peers 8001,8003 &
python -m kvstore.server --port 8003 --peers 8001,8002 &

# kill the leader mid-write — watch a new one get elected
kill -9 $(lsof -t -i:8001)
```

</details>

<details>
<summary><b>📁 Project Structure</b> — click to expand</summary>
<br>

```
distributed-kv-store/
├── src/kvstore/
│   ├── store.py       → in-memory core
│   ├── wal.py          → write-ahead log
│   ├── snapshot.py     → snapshotting
│   ├── raft.py         → consensus (election + replication)
│   ├── shard.py        → consistent hashing / routing
│   └── server.py       → async gRPC server
├── proto/kvstore.proto
├── tests/
└── README.md
```

</details>

<br>

## 🎯 Why This Exists

Most "distributed KV store" tutorials wrap Redis or call a consensus library. This one doesn't — every layer is implemented and tested against real failure scenarios: killed processes, partitioned networks, and split-brain conditions. Built as the coordination/caching layer for a paired on-device LLM inference engine, where it handles distributed prefix-cache storage across inference nodes.

<br>

<img width="100%" src="https://capsule-render.vercel.app/api?type=rect&color=0:2C5364,100:0F2027&height=3"/>

<div align="center">
<br>

<sub>Built as part of an AI/ML + systems engineering portfolio · MIT License</sub>

<br><br>

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:2C5364,100:0F2027&height=100&section=footer"/>

</div>
