# Milvus logical I/O trace and replay

This workflow records a small workload against a real Milvus instance, then
replays the same operation order and start-time spacing against a local disk.

## 1. Start Milvus on Windows

The Windows Compose file stores persistent data under
`C:\Users\Administrator\vdb_data`.

```powershell
docker compose -f docker-compose.win.yml up -d
docker compose -f docker-compose.win.yml ps
```

Wait until `milvus-etcd`, `milvus-minio`, and `milvus-standalone` all show
`healthy`. The first run can take several minutes while Docker pulls the
images; Milvus itself can need 90–120 seconds to become ready.

## 2. Record a live trace

From the repository virtual environment:

```powershell
python -m vdbbench.trace_runner `
  --num-vectors 1000 `
  --dimension 128 `
  --insert-batch-size 100 `
  --searches 100 `
  --top-k 10 `
  --drop-existing `
  --trace results\milvus_trace.csv
```

The output uses the same six columns as the KV-cache trace format:

```text
Timestamp,Operation,Object_Size_Bytes,Tier,Key,Phase
```

The runner records insert, flush, load, and search calls. Sizes are logical
estimates: insert payload bytes, total collection bytes for flush/load, and
query plus result-ID bytes for search. They are not Milvus filesystem bytes;
WAL, protobuf, object-store, index, metadata, and compaction amplification are
outside the client wrapper's visibility.

## 3. Replay on the target drive

```powershell
python -m vdbbench.replay results\milvus_trace.csv `
  --data-dir D:\vdb_replay_data `
  --direct-io
```

Replay is synchronous and preserves each row's start-time offset by default.
It reports P50/P95/P99 operation latency plus two throughput values:

- `wall-clock` includes the trace's intentional gaps.
- `active-I/O` divides bytes by time spent inside file reads/writes only.

Use `--as-fast-as-possible` to remove trace gaps, or `--speed 2` for a 2x replay.
On Windows, `--direct-io` uses sector-aligned unbuffered reads and write-through
writes. This bypasses the operating-system page cache and reports both the
logical trace bytes and the sector-padded bytes sent to the device. Use
`--fsync` instead for buffered reads with durable writes.

Replay files are deliberately raw binary rather than `.npz`: ZIP container
metadata and optional compression would make the physical request size differ
from `Object_Size_Bytes`.
