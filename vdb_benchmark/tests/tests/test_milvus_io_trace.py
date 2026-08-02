import csv

import numpy as np
import pytest

from vdbbench.benchmark.backends.milvus import backend as backend_module
from vdbbench.benchmark.backends.milvus.backend import MilvusBackend
from vdbbench.benchmark.run_benchmark import main as benchmark_main


class Hit:
    def __init__(self, hit_id):
        self.id = hit_id


class FakeCollection:
    def __init__(self, name):
        self.name = name
        self.calls = []

    def insert(self, data):
        self.calls.append(("insert", data))

    def flush(self):
        self.calls.append(("flush", None))

    def load(self):
        self.calls.append(("load", None))

    def search(self, **kwargs):
        self.calls.append(("search", kwargs))
        return [[Hit(10), Hit(20)]]


class VectorField:
    name = "vector"
    params = {"dim": 2}


class Schema:
    fields = [VectorField()]


def test_milvus_backend_records_formal_benchmark_operations(monkeypatch, tmp_path):
    collection = FakeCollection("formal_benchmark")
    connect_calls = []
    disconnect_calls = []
    monkeypatch.setattr(
        backend_module,
        "Collection",
        lambda name, **kwargs: collection,
    )
    monkeypatch.setattr(
        backend_module.connections,
        "connect",
        lambda *args, **kwargs: connect_calls.append((args, kwargs)),
    )
    monkeypatch.setattr(
        backend_module.connections,
        "disconnect",
        lambda alias: disconnect_calls.append(alias),
    )
    trace_path = tmp_path / "formal_trace.csv"
    backend = MilvusBackend()

    backend.connect(io_trace_log=str(trace_path))
    backend.insert_batch(
        "formal_benchmark",
        ids=np.array([1, 2], dtype=np.int64),
        vectors=np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32),
    )
    backend.flush("formal_benchmark")
    result = backend.search(
        "formal_benchmark",
        query_vectors=np.array([[5.0, 6.0]], dtype=np.float32),
        top_k=2,
        search_params={"metric_type": "L2", "params": {}},
    )
    backend.disconnect()

    with trace_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert result == [[10, 20]]
    assert [row["Operation"] for row in rows] == [
        "Write",
        "Write",
        "Read",
        "Read",
    ]
    assert [row["Phase"] for row in rows] == [
        "Insert",
        "Flush",
        "Load",
        "Search",
    ]
    assert [int(row["Object_Size_Bytes"]) for row in rows] == [32, 32, 32, 24]
    assert [row["Key"] for row in rows] == ["formal_benchmark"] * 4
    assert all(row["Tier"] == "Tier-2" for row in rows)
    assert len(connect_calls) == 1
    assert "io_trace_log" not in connect_calls[0][1]
    assert disconnect_calls == ["default"]


def test_formal_benchmark_cli_accepts_io_trace_log(monkeypatch, tmp_path, capsys):
    config_path = tmp_path / "benchmark.yaml"
    config_path.write_text(
        """\
backend: milvus
mode: both
dataset:
  collection_name: formal_benchmark
  num_vectors: 10
  dimension: 2
""",
        encoding="utf-8",
    )
    trace_path = tmp_path / "formal_trace.csv"
    monkeypatch.setenv("MILVUS__IO_TRACE_LOG", str(tmp_path / "environment.csv"))

    result = benchmark_main(
        [
            "--config",
            str(config_path),
            "--io-trace-log",
            str(trace_path),
            "--what-if",
        ]
    )

    output = capsys.readouterr().out
    assert result == 0
    assert '"io_trace_log"' in output
    assert trace_path.name in output
    assert "environment.csv" not in output


def test_search_only_trace_estimates_existing_collection_size(monkeypatch, tmp_path):
    collection = FakeCollection("existing_collection")
    collection.num_entities = 100
    collection.schema = Schema()
    monkeypatch.setattr(
        backend_module,
        "Collection",
        lambda name, **kwargs: collection,
    )
    monkeypatch.setattr(backend_module.connections, "connect", lambda *a, **kw: None)
    monkeypatch.setattr(backend_module.connections, "disconnect", lambda alias: None)
    trace_path = tmp_path / "search_only.csv"
    backend = MilvusBackend()

    backend.connect(io_trace_log=str(trace_path))
    backend.search(
        "existing_collection",
        query_vectors=np.array([[5.0, 6.0]], dtype=np.float32),
        top_k=2,
        search_params={"metric_type": "L2", "params": {}},
    )
    backend.disconnect()

    with trace_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert [row["Phase"] for row in rows] == ["Load", "Search"]
    assert [int(row["Object_Size_Bytes"]) for row in rows] == [1600, 24]


def test_io_trace_cli_rejects_non_milvus_backend(tmp_path, capsys):
    config_path = tmp_path / "benchmark.yaml"
    config_path.write_text(
        """\
backend: elasticsearch
mode: both
dataset:
  collection_name: formal_benchmark
  num_vectors: 10
  dimension: 2
""",
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as error:
        benchmark_main(
            [
                "--config",
                str(config_path),
                "--io-trace-log",
                str(tmp_path / "trace.csv"),
                "--what-if",
            ]
        )

    assert error.value.code == 2
    assert "--io-trace-log is only supported for Milvus" in capsys.readouterr().err
