"""Shared logical I/O trace contract for vector database workloads."""

from __future__ import annotations

import csv
import queue
import threading
from pathlib import Path


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
        self._queue: queue.SimpleQueue[list[object] | object] = queue.SimpleQueue()
        self._sentinel = object()
        self._lock = threading.Lock()
        self._closed = False
        self._worker_error: Exception | None = None
        self.event_count = 0
        self._worker = threading.Thread(
            target=self._write_rows,
            name="vdb-io-trace-writer",
            daemon=True,
        )
        self._worker.start()

    def _write_rows(self) -> None:
        try:
            while True:
                row = self._queue.get()
                if row is self._sentinel:
                    break
                self._writer.writerow(row)
            self._handle.flush()
        except Exception as error:
            self._worker_error = error

    def log(
        self,
        timestamp: float,
        operation: str,
        size_bytes: int,
        key: str,
        phase: str,
    ) -> None:
        row: list[object] = [
            f"{timestamp:.6f}",
            operation,
            int(size_bytes),
            "Tier-2",
            key,
            phase,
        ]
        with self._lock:
            if self._closed:
                return
            self._queue.put(row)
            self.event_count += 1

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._queue.put(self._sentinel)
        self._worker.join()
        self._handle.close()
        if self._worker_error is not None:
            raise RuntimeError("I/O trace writer failed") from self._worker_error

    def __enter__(self) -> TraceWriter:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()
