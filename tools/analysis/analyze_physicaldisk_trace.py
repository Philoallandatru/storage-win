#!/usr/bin/env python3
"""Summarize a Windows typeperf PhysicalDisk CSV capture.

The first row in a typeperf CSV is the counter header; later rows contain
sample timestamps and values.  The summary keeps the workload volume (for
example ``D:``) separate from ``_Total`` so a trace can be compared with the
logical workload and with a pSLC/TLC namespace mapping.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime
from pathlib import Path
from statistics import mean


def _number(value: str) -> float:
    value = (value or "").strip()
    if not value:
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def _timestamp(value: str) -> datetime | None:
    value = (value or "").strip()
    for fmt in ("%m/%d/%Y %H:%M:%S.%f", "%m/%d/%Y %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    return None


def summarize(path: Path, volume: str | None, interval_seconds: float) -> dict:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        raise ValueError(f"empty typeperf CSV: {path}")

    header = rows[0]
    samples = []
    for row in rows[1:]:
        if not row:
            continue
        timestamp = _timestamp(row[0])
        if timestamp is None:
            continue
        samples.append((timestamp, row))

    if volume:
        volume_re = re.compile(rf"PhysicalDisk\([^)]*\s{re.escape(volume.upper())}:\)")
        indexes = {
            "read_bytes_per_sec": next((i for i, name in enumerate(header) if volume_re.search(name) and name.endswith("Disk Read Bytes/sec")), None),
            "write_bytes_per_sec": next((i for i, name in enumerate(header) if volume_re.search(name) and name.endswith("Disk Write Bytes/sec")), None),
            "read_iops": next((i for i, name in enumerate(header) if volume_re.search(name) and name.endswith("Disk Reads/sec")), None),
            "write_iops": next((i for i, name in enumerate(header) if volume_re.search(name) and name.endswith("Disk Writes/sec")), None),
            "queue": next((i for i, name in enumerate(header) if volume_re.search(name) and name.endswith("Current Disk Queue Length")), None),
        }
    else:
        indexes = {
            "read_bytes_per_sec": next((i for i, name in enumerate(header) if "PhysicalDisk(_Total)" in name and name.endswith("Disk Read Bytes/sec")), None),
            "write_bytes_per_sec": next((i for i, name in enumerate(header) if "PhysicalDisk(_Total)" in name and name.endswith("Disk Write Bytes/sec")), None),
            "read_iops": next((i for i, name in enumerate(header) if "PhysicalDisk(_Total)" in name and name.endswith("Disk Reads/sec")), None),
            "write_iops": next((i for i, name in enumerate(header) if "PhysicalDisk(_Total)" in name and name.endswith("Disk Writes/sec")), None),
            "queue": next((i for i, name in enumerate(header) if "PhysicalDisk(_Total)" in name and name.endswith("Current Disk Queue Length")), None),
        }

    def values(key: str) -> list[float]:
        index = indexes[key]
        if index is None:
            return []
        return [_number(row[index]) if index < len(row) else 0.0 for _, row in samples]

    read_rate = values("read_bytes_per_sec")
    write_rate = values("write_bytes_per_sec")
    read_iops = values("read_iops")
    write_iops = values("write_iops")
    queue = values("queue")
    duration = 0.0
    if len(samples) > 1:
        duration = (samples[-1][0] - samples[0][0]).total_seconds()

    def stats(values_: list[float]) -> dict:
        return {
            "samples": len(values_),
            "avg": mean(values_) if values_ else 0.0,
            "peak": max(values_) if values_ else 0.0,
            "integrated": sum(values_) * interval_seconds,
        }

    return {
        "source": str(path),
        "volume": volume.upper() if volume else "_Total",
        "sample_interval_seconds": interval_seconds,
        "sample_count": len(samples),
        "duration_seconds": duration,
        "read": {"bytes_per_sec": stats(read_rate), "iops": stats(read_iops)},
        "write": {"bytes_per_sec": stats(write_rate), "iops": stats(write_iops)},
        "queue_length": stats(queue),
        "counter_columns_found": {key: index is not None for key, index in indexes.items()},
    }


def markdown(summary: dict) -> str:
    read = summary["read"]
    write = summary["write"]
    return "\n".join(
        [
            f"# PhysicalDisk trace summary — {summary['volume']}",
            "",
            f"- Source: `{summary['source']}`",
            f"- Samples/duration: {summary['sample_count']} / {summary['duration_seconds']:.3f}s",
            f"- Read: average {read['bytes_per_sec']['avg']:.0f} B/s, peak {read['bytes_per_sec']['peak']:.0f} B/s, integrated {read['bytes_per_sec']['integrated']:.0f} B",
            f"- Write: average {write['bytes_per_sec']['avg']:.0f} B/s, peak {write['bytes_per_sec']['peak']:.0f} B/s, integrated {write['bytes_per_sec']['integrated']:.0f} B",
            f"- Read/write IOPS peak: {read['iops']['peak']:.2f} / {write['iops']['peak']:.2f}",
            f"- Queue length peak: {summary['queue_length']['peak']:.2f}",
            "",
            "These are one-second host counters, not application-level operation sizes. Pair them with the logical trace and ETL for SSD-level attribution.",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("--volume", help="Drive letter, e.g. D; defaults to _Total")
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args()
    result = summarize(args.csv, args.volume, args.interval)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.json:
        args.json.write_text(payload, encoding="utf-8")
    if args.markdown:
        args.markdown.write_text(markdown(result), encoding="utf-8")
    if not args.json and not args.markdown:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
