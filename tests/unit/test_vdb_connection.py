"""Tests for local Milvus Lite and remote Milvus connection selection."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
VDB_BENCHMARK_DIR = ROOT_DIR / "vdb_benchmark"


def _run_probe(operation: str, **values) -> dict:
    """Run the connector probe in a clean interpreter.

    Several repository tests install optional-dependency stubs during module
    collection. A subprocess keeps those stubs, and the fake PyMilvus module
    used by this unit test, out of the parent pytest interpreter.
    """
    probe = r'''
import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

fake_pymilvus = types.ModuleType("pymilvus")
fake_pymilvus.connections = MagicMock(name="connections")
fake_pymilvus.Collection = MagicMock(name="Collection")
fake_pymilvus.CollectionSchema = MagicMock(name="CollectionSchema")
fake_pymilvus.DataType = MagicMock(name="DataType")
fake_pymilvus.FieldSchema = MagicMock(name="FieldSchema")
fake_pymilvus.utility = MagicMock(name="utility")
sys.modules["pymilvus"] = fake_pymilvus

from vdbbench import connection
from vdbbench.benchmark.backends.milvus.backend import MilvusBackend

values = json.loads(sys.argv[1])
operation = values["operation"]
with patch.object(connection.connections, "connect") as connect:
    if operation == "local_host":
        connection.open_connection(host=values["path"], port="19530")
        result = {"parent_exists": Path(values["path"]).parent.is_dir()}
    elif operation == "explicit_uri":
        connection.open_connection(
            host="ignored-host", port="19531", uri=values["path"]
        )
        result = {}
    elif operation == "remote":
        connection.open_connection(host=values["host"], port=19531)
        result = {}
    elif operation == "backend_uri":
        MilvusBackend().connect(uri=values["path"])
        result = {}
    else:
        raise ValueError(operation)

result["kwargs"] = connect.call_args.kwargs
print(json.dumps(result))
'''
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(VDB_BENCHMARK_DIR), env.get("PYTHONPATH", "")]
    )
    completed = subprocess.run(
        [sys.executable, "-c", probe, json.dumps({"operation": operation, **values})],
        cwd=ROOT_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"connection probe failed:\nstdout={completed.stdout}\nstderr={completed.stderr}"
        )
    return json.loads(completed.stdout.strip().splitlines()[-1])


class TestOpenConnection:
    def test_local_db_host_is_opened_as_milvus_lite_uri(self, tmp_path):
        db_path = tmp_path / "runtime" / "milvus.db"

        result = _run_probe("local_host", path=str(db_path))

        assert result["parent_exists"]
        kwargs = result["kwargs"]
        assert kwargs["uri"] == str(db_path.resolve())
        assert "host" not in kwargs
        assert "port" not in kwargs

    def test_explicit_uri_takes_precedence_over_host_and_port(self, tmp_path):
        db_path = tmp_path / "milvus.db"

        kwargs = _run_probe("explicit_uri", path=str(db_path))["kwargs"]

        assert kwargs["uri"] == str(db_path.resolve())

    def test_remote_endpoint_keeps_host_and_port_connection(self):
        kwargs = _run_probe("remote", host="10.0.0.8")["kwargs"]

        assert kwargs["host"] == "10.0.0.8"
        assert kwargs["port"] == "19531"
        assert "uri" not in kwargs

    def test_remote_db_hostname_is_not_treated_as_local_path(self):
        kwargs = _run_probe("remote", host="milvus.db")["kwargs"]

        assert kwargs["host"] == "milvus.db"
        assert "uri" not in kwargs


class TestMilvusBackend:
    def test_modular_backend_accepts_local_uri(self, tmp_path):
        db_path = tmp_path / "milvus.db"

        kwargs = _run_probe("backend_uri", path=str(db_path))["kwargs"]

        assert kwargs["uri"] == str(db_path.resolve())
        assert "host" not in kwargs
        assert "port" not in kwargs
