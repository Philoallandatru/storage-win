"""Record a small Milvus workload in the KV-cache I/O trace CSV format.

The byte counts in this trace are logical estimates.  They describe client
payloads and the collection bytes affected by flush/load, not Milvus' internal
filesystem I/O (WAL, object-store traffic, index amplification, and metadata).
"""

from __future__ import annotations

import argparse
import csv
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import numpy as np


TRACE_HEADER = [
    "Timestamp",
    "Operation",
    "Object_Size_Bytes",
    "Tier",
    "Key",
    "Phase",
]


class TraceWriter:
    """Write rows compatible with ``kv_cache_benchmark.kv_cache.tracer``."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._handle)
        self._writer.writerow(TRACE_HEADER)
        self.event_count = 0

    def log(
        self,
        timestamp: float,
        operation: str,
        size_bytes: int,
        key: str,
        phase: str,
    ) -> None:
        self._writer.writerow(
            [
                f"{timestamp:.6f}",
                operation,
                int(size_bytes),
                "Tier-2",
                key,
                phase,
            ]
        )
        self._handle.flush()
        self.event_count += 1

    def close(self) -> None:
        self._handle.close()

    def __enter__(self) -> TraceWriter:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()


def record_workload(
    *,
    collection: Any,
    vectors: np.ndarray,
    queries: np.ndarray,
    trace_path: str | Path,
    insert_batch_size: int = 100,
    top_k: int = 10,
    metric_type: str = "L2",
    clock: Callable[[], float] = time.time,
) -> int:
    """Run insert/flush/load/search calls and record their logical I/O.

    Insert sizes include float32 vector bytes plus int64 primary-key bytes.
    Flush and load use the total inserted logical size.  Search sizes include
    the query-vector payload plus one int64 result ID for each requested hit.
    Each timestamp records when the corresponding Milvus call starts.
    """

    vectors = np.ascontiguousarray(vectors, dtype=np.float32)
    queries = np.ascontiguousarray(queries, dtype=np.float32)
    if vectors.ndim != 2 or queries.ndim != 2:
        raise ValueError("vectors and queries must both be two-dimensional")
    if vectors.shape[1] != queries.shape[1]:
        raise ValueError("vectors and queries must have the same dimension")
    if insert_batch_size <= 0:
        raise ValueError("insert_batch_size must be positive")
    if top_k <= 0:
        raise ValueError("top_k must be positive")

    collection_key = str(collection.name)
    total_logical_bytes = 0

    with TraceWriter(trace_path) as trace:
        for start in range(0, len(vectors), insert_batch_size):
            batch = vectors[start : start + insert_batch_size]
            ids = np.arange(start, start + len(batch), dtype=np.int64)
            size_bytes = int(batch.nbytes + ids.nbytes)
            timestamp = clock()
            collection.insert([ids.tolist(), batch.tolist()])
            trace.log(timestamp, "Write", size_bytes, collection_key, "Insert")
            total_logical_bytes += size_bytes

        timestamp = clock()
        collection.flush()
        trace.log(
            timestamp,
            "Write",
            total_logical_bytes,
            collection_key,
            "Flush",
        )

        timestamp = clock()
        collection.load()
        trace.log(
            timestamp,
            "Read",
            total_logical_bytes,
            collection_key,
            "Load",
        )

        search_params = {"metric_type": metric_type, "params": {}}
        result_id_bytes = top_k * np.dtype(np.int64).itemsize
        for query in queries:
            query_batch = query.reshape(1, -1)
            size_bytes = int(query_batch.nbytes + result_id_bytes)
            timestamp = clock()
            collection.search(
                data=query_batch.tolist(),
                anns_field="vector",
                param=search_params,
                limit=top_k,
            )
            trace.log(timestamp, "Read", size_bytes, collection_key, "Search")

        return trace.event_count


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a small real Milvus workload and record a logical I/O trace."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default="19530")
    parser.add_argument("--collection", default="vdb_trace_vectors")
    parser.add_argument("--trace", type=Path, default=Path("trace.csv"))
    parser.add_argument("--num-vectors", type=_positive_int, default=1000)
    parser.add_argument("--dimension", type=_positive_int, default=128)
    parser.add_argument("--insert-batch-size", type=_positive_int, default=100)
    parser.add_argument("--searches", type=_positive_int, default=100)
    parser.add_argument("--top-k", type=_positive_int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--drop-existing",
        action="store_true",
        help="Drop a collection with the selected name before recording.",
    )
    parser.add_argument(
        "--keep-collection",
        action="store_true",
        help="Keep the generated collection after the trace completes.",
    )
    return parser


def run_live(args: argparse.Namespace) -> int:
    """Create a temporary FLAT collection and record a live Milvus trace."""

    from pymilvus import (
        Collection,
        CollectionSchema,
        DataType,
        FieldSchema,
        connections,
        utility,
    )

    from vdbbench.connection import open_connection

    if args.top_k > args.num_vectors:
        raise ValueError("top-k cannot exceed num-vectors")

    open_connection(host=args.host, port=args.port)
    created = False
    try:
        if utility.has_collection(args.collection):
            if not args.drop_existing:
                raise RuntimeError(
                    f"collection {args.collection!r} already exists; "
                    "choose another name or pass --drop-existing"
                )
            utility.drop_collection(args.collection)

        schema = CollectionSchema(
            fields=[
                FieldSchema(
                    name="id",
                    dtype=DataType.INT64,
                    is_primary=True,
                    auto_id=False,
                ),
                FieldSchema(
                    name="vector",
                    dtype=DataType.FLOAT_VECTOR,
                    dim=args.dimension,
                ),
            ],
            description="Temporary logical I/O trace workload",
        )
        collection = Collection(args.collection, schema=schema)
        created = True
        collection.create_index(
            "vector",
            {"index_type": "FLAT", "metric_type": "L2", "params": {}},
        )

        rng = np.random.default_rng(args.seed)
        vectors = rng.random(
            (args.num_vectors, args.dimension), dtype=np.float32
        )
        queries = rng.random((args.searches, args.dimension), dtype=np.float32)
        event_count = record_workload(
            collection=collection,
            vectors=vectors,
            queries=queries,
            trace_path=args.trace,
            insert_batch_size=args.insert_batch_size,
            top_k=args.top_k,
        )
        print(
            f"Recorded {event_count} events for {args.num_vectors} vectors and "
            f"{args.searches} searches to {args.trace.resolve()}"
        )
        return event_count
    finally:
        if created and not args.keep_collection:
            utility.drop_collection(args.collection)
        connections.disconnect("default")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run_live(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
