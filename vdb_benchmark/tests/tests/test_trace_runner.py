import csv

import numpy as np

from vdbbench.trace_runner import record_workload


class FakeCollection:
    name = "trace_vectors"

    def __init__(self):
        self.calls = []

    def insert(self, data):
        self.calls.append(("insert", len(data[0])))

    def flush(self):
        self.calls.append(("flush", None))

    def load(self):
        self.calls.append(("load", None))

    def search(self, **kwargs):
        self.calls.append(("search", len(kwargs["data"])))
        return [[object(), object()]]


def test_record_workload_writes_kv_compatible_trace(tmp_path):
    collection = FakeCollection()
    vectors = np.arange(6, dtype=np.float32).reshape(3, 2)
    queries = np.arange(4, dtype=np.float32).reshape(2, 2)
    timestamps = iter([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
    trace_path = tmp_path / "trace.csv"

    event_count = record_workload(
        collection=collection,
        vectors=vectors,
        queries=queries,
        trace_path=trace_path,
        insert_batch_size=2,
        top_k=2,
        clock=lambda: next(timestamps),
    )

    with trace_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert event_count == 6
    assert list(rows[0]) == [
        "Timestamp",
        "Operation",
        "Object_Size_Bytes",
        "Tier",
        "Key",
        "Phase",
    ]
    assert [row["Timestamp"] for row in rows] == [
        "100.000000",
        "101.000000",
        "102.000000",
        "103.000000",
        "104.000000",
        "105.000000",
    ]
    assert [row["Operation"] for row in rows] == [
        "Write",
        "Write",
        "Write",
        "Read",
        "Read",
        "Read",
    ]
    assert [int(row["Object_Size_Bytes"]) for row in rows] == [
        32,
        16,
        48,
        48,
        24,
        24,
    ]
    assert [row["Tier"] for row in rows] == ["Tier-2"] * 6
    assert [row["Key"] for row in rows] == ["trace_vectors"] * 6
    assert [row["Phase"] for row in rows] == [
        "Insert",
        "Insert",
        "Flush",
        "Load",
        "Search",
        "Search",
    ]
    assert collection.calls == [
        ("insert", 2),
        ("insert", 1),
        ("flush", None),
        ("load", None),
        ("search", 1),
        ("search", 1),
    ]
