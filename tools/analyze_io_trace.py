"""Summarize KV-compatible logical I/O traces for AI workload analysis.

The analyzer accepts the common trace schema used by the VectorDB and KV-cache
tools in this repository:

    Timestamp,Operation,Object_Size_Bytes,Tier,Key,Phase

It deliberately reports logical trace characteristics separately from device
I/O. A trace row is a workload description; it is not proof of a physical
NVMe request. PhysicalDisk/ETW measurements should be joined by run_id when a
trace is replayed against a Windows namespace.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


TRACE_HEADER = ["Timestamp", "Operation", "Object_Size_Bytes", "Tier", "Key", "Phase"]


@dataclass(frozen=True)
class TraceEvent:
    timestamp: float
    operation: str
    size_bytes: int
    tier: str
    key: str
    phase: str


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    if len(values) == 1:
        return float(values[0])
    rank = (percentile / 100.0) * (len(values) - 1)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return float(values[lower])
    weight = rank - lower
    return float(values[lower] + (values[upper] - values[lower]) * weight)


def _mib(value: int | float) -> float:
    return float(value) / (1024.0 * 1024.0)


def load_trace(path: Path) -> list[TraceEvent]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != TRACE_HEADER:
            raise ValueError(
                f"{path}: expected header {TRACE_HEADER!r}, got {reader.fieldnames!r}"
            )
        events: list[TraceEvent] = []
        previous: float | None = None
        for row_number, row in enumerate(reader, start=2):
            try:
                timestamp = float(row["Timestamp"])
                size_bytes = int(row["Object_Size_Bytes"])
            except (TypeError, ValueError) as error:
                raise ValueError(f"{path}: invalid timestamp/size at row {row_number}") from error
            if timestamp < 0 or size_bytes < 0:
                raise ValueError(f"{path}: negative timestamp/size at row {row_number}")
            operation = str(row["Operation"])
            if operation not in {"Read", "Write"}:
                raise ValueError(f"{path}: unsupported operation {operation!r} at row {row_number}")
            key = str(row["Key"]).strip()
            if not key:
                raise ValueError(f"{path}: empty key at row {row_number}")
            events.append(
                TraceEvent(
                    timestamp=timestamp,
                    operation=operation,
                    size_bytes=size_bytes,
                    tier=str(row["Tier"]),
                    key=key,
                    phase=str(row["Phase"]),
                )
            )
            previous = timestamp
    if not events:
        raise ValueError(f"{path}: trace contains no events")
    return events


def _profile_label(events: list[TraceEvent]) -> str:
    sizes = [event.size_bytes for event in events]
    reads = sum(event.operation == "Read" for event in events)
    writes = len(events) - reads
    median_size = _percentile([float(x) for x in sizes], 50)
    read_ratio = reads / len(events)
    write_ratio = writes / len(events)
    if median_size <= 64 * 1024 and (read_ratio >= 0.65 or write_ratio >= 0.65):
        return "small-object I/O"
    if write_ratio >= 0.65 and median_size >= 1024 * 1024:
        return "large-object write"
    if read_ratio >= 0.65:
        return "read-dominant"
    if write_ratio >= 0.65:
        return "write-dominant"
    return "mixed I/O"


def summarize(path: Path, label: str | None = None) -> dict[str, object]:
    events = load_trace(path)
    timestamps = [event.timestamp for event in events]
    sizes = [event.size_bytes for event in events]
    raw_gaps_ms = [
        (events[index].timestamp - events[index - 1].timestamp) * 1000.0
        for index in range(1, len(events))
    ]
    timestamp_regressions = [gap for gap in raw_gaps_ms if gap < 0]
    gaps_ms = [gap for gap in raw_gaps_ms if gap >= 0]
    op_counts = Counter(event.operation for event in events)
    op_bytes = Counter()
    for event in events:
        op_bytes[event.operation] += event.size_bytes

    duration = max(0.0, timestamps[-1] - timestamps[0])
    total_bytes = sum(sizes)
    unique_keys = len({event.key for event in events})
    nonzero = sum(size > 0 for size in sizes)
    bucket_counts = Counter()
    for size in sizes:
        if size <= 4 * 1024:
            bucket_counts["<=4KiB"] += 1
        elif size <= 64 * 1024:
            bucket_counts["4KiB-64KiB"] += 1
        elif size <= 1024 * 1024:
            bucket_counts["64KiB-1MiB"] += 1
        else:
            bucket_counts[">1MiB"] += 1

    read_ratio = op_counts["Read"] / len(events)
    write_ratio = op_counts["Write"] / len(events)
    notes: list[str] = [
        "Logical trace only; use PhysicalDisk/ETW during replay for physical I/O.",
    ]
    if timestamp_regressions:
        notes.append(
            f"Timestamp order is not monotonic for {len(timestamp_regressions)} adjacent pairs "
            "(likely concurrent logging); replay requires an ordering policy."
        )
    if duration == 0:
        notes.append("All events share one timestamp or the run is too short for a timing profile.")
    if unique_keys < len(events):
        notes.append("Repeated keys indicate object reuse or repeated reads; inspect phase/tier distribution.")
    if not nonzero:
        notes.append("All operations have zero logical size; do not use for SSD bandwidth analysis.")
    if read_ratio >= 0.8:
        notes.append("Read-heavy profile; compare cache-hit and cold/reboot-cold runs.")
    if write_ratio >= 0.8:
        notes.append("Write-heavy profile; compare fill level, temperature and recovery time.")

    return {
        "trace": str(path),
        "label": label or path.stem,
        "schema": TRACE_HEADER,
        "profile": _profile_label(events),
        "event_count": len(events),
        "unique_keys": unique_keys,
        "first_timestamp": timestamps[0],
        "last_timestamp": timestamps[-1],
        "timestamp_regressions": len(timestamp_regressions),
        "largest_timestamp_regression_ms": abs(min(timestamp_regressions)) if timestamp_regressions else 0.0,
        "duration_seconds": duration,
        "events_per_second": len(events) / duration if duration else 0.0,
        "logical_bytes": total_bytes,
        "logical_mib": _mib(total_bytes),
        "logical_mib_per_second": _mib(total_bytes) / duration if duration else 0.0,
        "read_count": op_counts["Read"],
        "write_count": op_counts["Write"],
        "read_ratio": read_ratio,
        "write_ratio": write_ratio,
        "read_bytes": op_bytes["Read"],
        "write_bytes": op_bytes["Write"],
        "size_bytes": {
            "p50": _percentile([float(x) for x in sizes], 50),
            "p95": _percentile([float(x) for x in sizes], 95),
            "p99": _percentile([float(x) for x in sizes], 99),
            "min": min(sizes),
            "max": max(sizes),
        },
        "interarrival_ms": {
            "p50": _percentile(gaps_ms, 50),
            "p95": _percentile(gaps_ms, 95),
            "p99": _percentile(gaps_ms, 99),
            "max": max(gaps_ms) if gaps_ms else 0.0,
        },
        "operation_counts": dict(op_counts),
        "operation_bytes": dict(op_bytes),
        "tier_counts": dict(Counter(event.tier for event in events)),
        "phase_counts": dict(Counter(event.phase for event in events)),
        "size_buckets": dict(bucket_counts),
        "notes": notes,
    }


def _fmt(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def write_report(summaries: list[dict[str, object]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "trace_summary.json").write_text(
        json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    profile_header = [
        "label", "profile", "events", "unique_keys", "duration_s", "events_per_s",
        "logical_mib", "logical_mib_per_s", "read_ratio", "write_ratio",
        "size_p50_bytes", "size_p95_bytes", "size_p99_bytes", "gap_p50_ms", "gap_p95_ms",
    ]
    with (output_dir / "trace_profiles.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(profile_header)
        for item in summaries:
            writer.writerow([
                item["label"], item["profile"], item["event_count"], item["unique_keys"],
                item["duration_seconds"], item["events_per_second"], item["logical_mib"],
                item["logical_mib_per_second"], item["read_ratio"], item["write_ratio"],
                item["size_bytes"]["p50"], item["size_bytes"]["p95"], item["size_bytes"]["p99"],
                item["interarrival_ms"]["p50"], item["interarrival_ms"]["p95"],
            ])

    lines = [
        "# AI workload I/O trace analysis",
        "",
        "> These are logical trace profiles. Physical I/O must be joined from Windows PhysicalDisk/ETW data collected during replay.",
        "",
        "| Label | Profile | Events | Logical MiB | Read/Write | Size P50/P95/P99 | Gap P50/P95 |",
        "|---|---|---:|---:|---|---|---|",
    ]
    for item in summaries:
        sizes = item["size_bytes"]
        gaps = item["interarrival_ms"]
        lines.append(
            f"| {item['label']} | {item['profile']} | {item['event_count']} | "
            f"{_fmt(item['logical_mib'])} | {item['read_ratio']:.1%}/{item['write_ratio']:.1%} | "
            f"{_fmt(sizes['p50'])}/{_fmt(sizes['p95'])}/{_fmt(sizes['p99'])} B | "
            f"{_fmt(gaps['p50'])}/{_fmt(gaps['p95'])} ms |"
        )
    lines.extend(["", "## Per-trace notes", ""])
    for item in summaries:
        lines.append(f"### {item['label']}")
        lines.append("")
        for note in item["notes"]:
            lines.append(f"- {note}")
        lines.append(f"- Tiers: `{json.dumps(item['tier_counts'], ensure_ascii=False)}`")
        lines.append(f"- Phases: `{json.dumps(item['phase_counts'], ensure_ascii=False)}`")
        lines.append(f"- Size buckets: `{json.dumps(item['size_buckets'], ensure_ascii=False)}`")
        lines.append("")
    (output_dir / "trace_report.md").write_text("\n".join(lines), encoding="utf-8")


def _parse_trace_arg(value: str) -> tuple[str | None, Path]:
    if "=" in value:
        label, raw_path = value.split("=", 1)
        if label and raw_path:
            return label, Path(raw_path)
    return None, Path(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze KV-compatible AI workload I/O traces.")
    parser.add_argument(
        "--trace", action="append", required=True,
        help="Trace path, optionally label=path. Repeat for multiple scenarios.",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    summaries = []
    for value in args.trace:
        label, path = _parse_trace_arg(value)
        summaries.append(summarize(path, label))
    write_report(summaries, args.output_dir)
    print(json.dumps({"traces": len(summaries), "output_dir": str(args.output_dir)}, ensure_ascii=False))
    for item in summaries:
        print(
            f"{item['label']}: profile={item['profile']} events={item['event_count']} "
            f"logical_mib={item['logical_mib']:.3f} read_ratio={item['read_ratio']:.3f} "
            f"size_p99={item['size_bytes']['p99']:.0f}B"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
