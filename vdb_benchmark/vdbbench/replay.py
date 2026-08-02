"""Replay KV-compatible logical I/O traces against a local filesystem."""

from __future__ import annotations

import argparse
import csv
import os
import re
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import numpy as np

from vdbbench.trace_runner import TRACE_HEADER


@dataclass(frozen=True)
class TraceEvent:
    timestamp: float
    operation: str
    size_bytes: int
    key: str
    phase: str
    row_number: int


@dataclass(frozen=True)
class ReplaySummary:
    operation_count: int
    read_count: int
    write_count: int
    total_bytes: int
    read_bytes: int
    write_bytes: int
    device_bytes: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    wall_seconds: float
    io_seconds: float
    wall_throughput_mib_s: float
    io_throughput_mib_s: float
    device_throughput_mib_s: float


def load_trace(path: str | Path) -> list[TraceEvent]:
    """Parse and validate a KV-cache-compatible CSV trace."""

    trace_path = Path(path)
    events: list[TraceEvent] = []
    with trace_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != TRACE_HEADER:
            raise ValueError(
                f"trace header must be {TRACE_HEADER!r}, got {reader.fieldnames!r}"
            )
        previous_timestamp: float | None = None
        for row_number, row in enumerate(reader, start=2):
            try:
                timestamp = float(row["Timestamp"])
                size_bytes = int(row["Object_Size_Bytes"])
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"invalid timestamp or byte size at CSV row {row_number}"
                ) from error
            operation = row["Operation"]
            if operation not in {"Read", "Write"}:
                raise ValueError(
                    f"unsupported operation {operation!r} at CSV row {row_number}"
                )
            if size_bytes < 0:
                raise ValueError(f"negative byte size at CSV row {row_number}")
            if previous_timestamp is not None and timestamp < previous_timestamp:
                raise ValueError(
                    f"timestamps go backwards at CSV row {row_number}"
                )
            key = row["Key"].strip()
            if not key:
                raise ValueError(f"empty object key at CSV row {row_number}")
            events.append(
                TraceEvent(
                    timestamp=timestamp,
                    operation=operation,
                    size_bytes=size_bytes,
                    key=key,
                    phase=row["Phase"],
                    row_number=row_number,
                )
            )
            previous_timestamp = timestamp
    if not events:
        raise ValueError("trace contains no events")
    return events


def _object_path(data_dir: Path, key: str) -> Path:
    normalized = PurePosixPath(key.replace("\\", "/"))
    if normalized.is_absolute() or any(part in {"", ".", ".."} for part in normalized.parts):
        raise ValueError(f"unsafe object key: {key!r}")
    safe_parts = [re.sub(r"[^A-Za-z0-9._-]", "_", part) for part in normalized.parts]
    target = data_dir.joinpath(*safe_parts)
    target = target.with_name(f"{target.name}.bin")
    root = data_dir.resolve()
    resolved = target.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"object key escapes replay directory: {key!r}")
    return target


def _write_exact(
    path: Path,
    size_bytes: int,
    rng: np.random.Generator,
    chunk_size: int,
    fsync_writes: bool,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    remaining = size_bytes
    with path.open("wb", buffering=0) as handle:
        while remaining:
            current_size = min(remaining, chunk_size)
            chunk = rng.integers(0, 256, size=current_size, dtype=np.uint8)
            handle.write(chunk)
            remaining -= current_size
        if fsync_writes:
            os.fsync(handle.fileno())


def _read_exact(path: Path, size_bytes: int, chunk_size: int, row_number: int) -> None:
    try:
        handle = path.open("rb", buffering=0)
    except FileNotFoundError as error:
        raise ValueError(
            f"read at CSV row {row_number} has no prior object: {path}"
        ) from error
    remaining = size_bytes
    with handle:
        while remaining:
            chunk = handle.read(min(remaining, chunk_size))
            if not chunk:
                raise ValueError(
                    f"object is shorter than requested at CSV row {row_number}: {path}"
                )
            remaining -= len(chunk)


def replay_trace(
    *,
    trace_path: str | Path,
    data_dir: str | Path,
    respect_timing: bool = True,
    speed: float = 1.0,
    fsync_writes: bool = False,
    chunk_size: int = 4 * 1024 * 1024,
    random_seed: int = 42,
    direct_io: bool = False,
    monotonic: Callable[[], float] = time.perf_counter,
    sleeper: Callable[[float], None] = time.sleep,
) -> ReplaySummary:
    """Replay every trace row synchronously and return latency/throughput data."""

    if speed <= 0:
        raise ValueError("speed must be positive")
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    events = load_trace(trace_path)
    root = Path(data_dir)
    root.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(random_seed)
    direct_backend = None
    if direct_io:
        from vdbbench.windows_direct_io import WindowsDirectIO

        direct_backend = WindowsDirectIO(
            root,
            chunk_size=chunk_size,
            random_seed=random_seed,
        )
    first_timestamp = events[0].timestamp
    wall_start = monotonic()
    latencies_ms: list[float] = []

    read_count = 0
    write_count = 0
    read_bytes = 0
    write_bytes = 0
    device_bytes = 0

    for event in events:
        if respect_timing:
            target = wall_start + (event.timestamp - first_timestamp) / speed
            delay = target - monotonic()
            if delay > 0:
                sleeper(delay)

        path = _object_path(root, event.key)
        operation_start = monotonic()
        if event.operation == "Write":
            if direct_backend is None:
                _write_exact(path, event.size_bytes, rng, chunk_size, fsync_writes)
                device_bytes += event.size_bytes
            else:
                device_bytes += direct_backend.write(path, event.size_bytes)
            write_count += 1
            write_bytes += event.size_bytes
        else:
            if direct_backend is None:
                _read_exact(path, event.size_bytes, chunk_size, event.row_number)
                device_bytes += event.size_bytes
            else:
                device_bytes += direct_backend.read(
                    path, event.size_bytes, event.row_number
                )
            read_count += 1
            read_bytes += event.size_bytes
        latencies_ms.append((monotonic() - operation_start) * 1000.0)

    wall_seconds = max(0.0, monotonic() - wall_start)
    io_seconds = sum(latencies_ms) / 1000.0
    total_bytes = read_bytes + write_bytes
    p50_ms, p95_ms, p99_ms = np.percentile(latencies_ms, [50, 95, 99])
    mib = total_bytes / (1024 * 1024)
    device_mib = device_bytes / (1024 * 1024)
    return ReplaySummary(
        operation_count=len(events),
        read_count=read_count,
        write_count=write_count,
        total_bytes=total_bytes,
        read_bytes=read_bytes,
        write_bytes=write_bytes,
        device_bytes=device_bytes,
        p50_ms=float(p50_ms),
        p95_ms=float(p95_ms),
        p99_ms=float(p99_ms),
        wall_seconds=wall_seconds,
        io_seconds=io_seconds,
        wall_throughput_mib_s=mib / wall_seconds if wall_seconds else 0.0,
        io_throughput_mib_s=mib / io_seconds if io_seconds else 0.0,
        device_throughput_mib_s=(
            device_mib / io_seconds if io_seconds else 0.0
        ),
    )


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Replay a KV-compatible logical I/O trace against local storage."
    )
    parser.add_argument("trace", type=Path)
    parser.add_argument("--data-dir", type=Path, default=Path("replay_data"))
    parser.add_argument(
        "--speed",
        type=_positive_float,
        default=1.0,
        help="Timing multiplier: 2 replays twice as fast (default: 1).",
    )
    parser.add_argument(
        "--as-fast-as-possible",
        action="store_true",
        help="Ignore trace gaps while preserving row order.",
    )
    parser.add_argument(
        "--fsync",
        action="store_true",
        help="Force each write to stable storage before recording its latency.",
    )
    parser.add_argument(
        "--direct-io",
        action="store_true",
        help=(
            "Bypass the Windows page cache with aligned, unbuffered reads and "
            "write-through writes."
        ),
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--chunk-size-mib", type=_positive_float, default=4.0)
    return parser


def print_summary(summary: ReplaySummary) -> None:
    print(
        f"Operations: {summary.operation_count} "
        f"({summary.write_count} writes, {summary.read_count} reads)"
    )
    print(
        f"Data: {summary.total_bytes / (1024 * 1024):.3f} MiB "
        f"({summary.write_bytes / (1024 * 1024):.3f} MiB written, "
        f"{summary.read_bytes / (1024 * 1024):.3f} MiB read)"
    )
    print(
        f"Latency: P50={summary.p50_ms:.3f} ms  "
        f"P95={summary.p95_ms:.3f} ms  P99={summary.p99_ms:.3f} ms"
    )
    print(
        f"Throughput: {summary.wall_throughput_mib_s:.3f} MiB/s wall-clock  "
        f"{summary.io_throughput_mib_s:.3f} MiB/s active-I/O"
    )
    if summary.device_bytes != summary.total_bytes:
        print(
            f"Device I/O: {summary.device_bytes / (1024 * 1024):.3f} MiB "
            f"after sector padding  "
            f"{summary.device_throughput_mib_s:.3f} MiB/s active-I/O"
        )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = replay_trace(
        trace_path=args.trace,
        data_dir=args.data_dir,
        respect_timing=not args.as_fast_as_possible,
        speed=args.speed,
        fsync_writes=args.fsync,
        chunk_size=max(1, int(args.chunk_size_mib * 1024 * 1024)),
        random_seed=args.seed,
        direct_io=args.direct_io,
    )
    print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
