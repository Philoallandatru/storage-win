import csv
import os

import pytest

from vdbbench.replay import replay_trace


def test_replay_executes_file_io_and_reports_summary(tmp_path):
    trace_path = tmp_path / "trace.csv"
    with trace_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "Timestamp",
                "Operation",
                "Object_Size_Bytes",
                "Tier",
                "Key",
                "Phase",
            ]
        )
        writer.writerow(["1.000000", "Write", "16", "Tier-2", "collection", "Insert"])
        writer.writerow(["1.010000", "Read", "8", "Tier-2", "collection", "Search"])
        writer.writerow(["1.020000", "Write", "4", "Tier-2", "nested/object", "Insert"])

    data_dir = tmp_path / "replay-data"
    summary = replay_trace(
        trace_path=trace_path,
        data_dir=data_dir,
        respect_timing=False,
        random_seed=7,
    )

    assert summary.operation_count == 3
    assert summary.read_count == 1
    assert summary.write_count == 2
    assert summary.total_bytes == 28
    assert summary.read_bytes == 8
    assert summary.write_bytes == 20
    assert summary.p50_ms >= 0
    assert summary.p95_ms >= summary.p50_ms
    assert summary.p99_ms >= summary.p95_ms
    assert summary.wall_throughput_mib_s >= 0
    assert summary.io_throughput_mib_s >= 0
    assert (data_dir / "collection.bin").stat().st_size == 16
    assert (data_dir / "nested" / "object.bin").stat().st_size == 4


@pytest.mark.skipif(os.name != "nt", reason="Windows direct I/O implementation")
def test_replay_can_bypass_windows_file_cache(tmp_path):
    trace_path = tmp_path / "trace.csv"
    with trace_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "Timestamp",
                "Operation",
                "Object_Size_Bytes",
                "Tier",
                "Key",
                "Phase",
            ]
        )
        writer.writerow(["1.000000", "Write", "513", "Tier-2", "object", "Insert"])
        writer.writerow(["1.010000", "Read", "513", "Tier-2", "object", "Search"])

    summary = replay_trace(
        trace_path=trace_path,
        data_dir=tmp_path / "direct-data",
        respect_timing=False,
        direct_io=True,
    )

    assert summary.total_bytes == 1026
    assert summary.device_bytes >= 8192
    assert summary.device_bytes % 4096 == 0


def test_replay_prepares_objects_for_search_only_trace(tmp_path):
    trace_path = tmp_path / "search_only.csv"
    with trace_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "Timestamp",
                "Operation",
                "Object_Size_Bytes",
                "Tier",
                "Key",
                "Phase",
            ]
        )
        writer.writerow(["1.000000", "Read", "16", "Tier-2", "existing", "Load"])
        writer.writerow(["1.010000", "Read", "8", "Tier-2", "existing", "Search"])

    summary = replay_trace(
        trace_path=trace_path,
        data_dir=tmp_path / "search-only-data",
        respect_timing=False,
    )

    assert summary.operation_count == 2
    assert summary.read_count == 2
    assert summary.write_count == 0
    assert summary.total_bytes == 24
    assert (tmp_path / "search-only-data" / "existing.bin").stat().st_size == 16
