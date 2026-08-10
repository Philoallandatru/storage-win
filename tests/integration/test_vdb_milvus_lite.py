"""Optional live Milvus Lite smoke test.

Run with ``RUN_MILVUS_LITE_INTEGRATION=1`` on a supported Linux/macOS/WSL
environment after installing ``pymilvus[milvus-lite]``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


ROOT_DIR = Path(__file__).resolve().parents[2]
VDB_BENCHMARK_DIR = ROOT_DIR / "vdb_benchmark"
if str(VDB_BENCHMARK_DIR) not in sys.path:
    sys.path.insert(0, str(VDB_BENCHMARK_DIR))


@pytest.mark.skipif(
    os.environ.get("RUN_MILVUS_LITE_INTEGRATION") != "1",
    reason="set RUN_MILVUS_LITE_INTEGRATION=1 to run the live Milvus Lite test",
)
def test_open_connection_starts_milvus_lite(tmp_path):
    pytest.importorskip("milvus_lite")
    from pymilvus import MilvusClient, connections

    from vdbbench.connection import open_connection

    db_path = tmp_path / "milvus_lite.db"
    open_connection(uri=str(db_path))
    client = MilvusClient(str(db_path))
    collection_name = "vdb_lite_smoke"

    try:
        client.create_collection(collection_name, dimension=4, metric_type="COSINE")
        client.insert(
            collection_name,
            [
                {"id": 1, "vector": [1.0, 0.0, 0.0, 0.0]},
                {"id": 2, "vector": [0.0, 1.0, 0.0, 0.0]},
            ],
        )
        hits = client.search(
            collection_name,
            data=[[1.0, 0.0, 0.0, 0.0]],
            limit=1,
        )
        assert hits and hits[0][0]["id"] == 1
    finally:
        client.drop_collection(collection_name)
        client.close()
        connections.disconnect("default")
