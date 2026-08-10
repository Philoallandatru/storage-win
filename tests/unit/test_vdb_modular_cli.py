"""Tests for the modular VectorDB runner's local URI option."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
VDB_BENCHMARK_DIR = ROOT_DIR / "vdb_benchmark"


def test_modular_runner_accepts_milvus_uri():
    probe = r'''
import json
import sys
import types
from unittest.mock import MagicMock

fake_pymilvus = types.ModuleType("pymilvus")
fake_pymilvus.connections = MagicMock(name="connections")
fake_pymilvus.Collection = MagicMock(name="Collection")
fake_pymilvus.CollectionSchema = MagicMock(name="CollectionSchema")
fake_pymilvus.DataType = MagicMock(name="DataType")
fake_pymilvus.FieldSchema = MagicMock(name="FieldSchema")
fake_pymilvus.utility = MagicMock(name="utility")
sys.modules["pymilvus"] = fake_pymilvus

from vdbbench.benchmark.run_benchmark import _build_parser, _merge_cli_over_yaml

parser = _build_parser()
args = parser.parse_args([
    "--config", "config.yaml",
    "--milvus-uri", "runtime/milvus.db",
])
print(json.dumps(_merge_cli_over_yaml({}, args)["uri"]))
'''
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(VDB_BENCHMARK_DIR), env.get("PYTHONPATH", "")]
    )
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=ROOT_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout.strip().splitlines()[-1]) == (
        "runtime/milvus.db"
    )
