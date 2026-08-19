"""Tests for the MIX family (concurrent KV Cache on C: + VectorDB on E:).

Covers:
  1. ``case_catalog.json`` ships ``AI-MIX-001`` with a ``MIX`` family and
     ``stream``-tagged native_commands (kv / vdb).
  2. ``run_case._build_commands`` substitutes the dual-drive placeholders:
     KV stream -> primary data dir (C:), VDB stream -> secondary dir (E:).
  3. ``shrink_args`` returns low-pressure overrides for MIX.
"""

from __future__ import annotations

import json
from pathlib import Path

from full_test_plan_cases.catalog import get_case, load_catalog
from full_test_plan_cases.run_case import Overrides, _build_commands
from full_test_plan_cases.shrink import case_family, shrink_args

REPO = Path(__file__).resolve().parents[2]
CATALOG = REPO / "full_test_plan_cases" / "case_catalog.json"


def test_catalog_contains_mix_001():
    catalog = load_catalog()
    case = get_case("AI-MIX-001")
    assert case["family"] == "MIX"
    streams = [nc.get("stream") for nc in case["native_commands"]]
    assert streams == ["kv", "vdb", "vdb"]


def test_mix_build_commands_dual_drive():
    case = get_case("AI-MIX-001")
    data_dir = Path("C:/MLPerfStorageTest/data")
    vdb_dir = Path("E:/MLPerfStorageTest/data")
    overrides = Overrides(allow_invalid_params=True, skip_fs_separation_gate=True)
    commands, streams = _build_commands(
        case,
        data_dir=data_dir,
        results_dir=Path("C:/MLPerfStorageTest/results"),
        systemname="mix-test",
        mpi_bin="mpiexec",
        client_memory_gb=32,
        accelerators=1,
        query_processes=1,
        duration_sec=10,
        loops=1,
        prepare=True,
        overrides=overrides,
        vdb_data_dir=vdb_dir,
    )
    assert streams == ["kv", "vdb", "vdb"]
    assert len(commands) == 3

    kv_cmd, vdb_datagen, vdb_run = commands
    # KV stream uses the PRIMARY data drive (C:)
    kv_cache_idx = kv_cmd.index("--cache-dir")
    kv_path = kv_cmd[kv_cache_idx + 1].replace("\\", "/")
    assert kv_path.startswith("C:/MLPerfStorageTest/data")
    assert "AI-MIX-001" in kv_path

    # VDB stream uses the SECONDARY data drive (E:)
    vdb_root_idx = vdb_run.index("--storage-root")
    vdb_path = vdb_run[vdb_root_idx + 1].replace("\\", "/")
    assert vdb_path.startswith("E:/MLPerfStorageTest/data")
    assert "AI-MIX-001" in vdb_path

    # VDB datagen does not carry storage-root (results-dir derived), but run does
    assert "--storage-root" not in vdb_datagen


def test_mix_build_commands_defaults_to_primary_when_no_vdb_dir():
    """Without vdb_data_dir the VDB stream falls back to the primary data dir."""
    case = get_case("AI-MIX-001")
    overrides = Overrides()
    commands, _ = _build_commands(
        case,
        data_dir=Path("C:/MLPerfStorageTest/data"),
        results_dir=Path("C:/MLPerfStorageTest/results"),
        systemname="mix-test",
        mpi_bin="mpiexec",
        client_memory_gb=32,
        accelerators=1,
        query_processes=1,
        duration_sec=10,
        loops=1,
        prepare=True,
        overrides=overrides,
    )
    vdb_run = commands[2]
    vdb_root_idx = vdb_run.index("--storage-root")
    vdb_path = vdb_run[vdb_root_idx + 1].replace("\\", "/")
    assert vdb_path.startswith("C:/MLPerfStorageTest/data")


def test_mix_shrink_args_low_pressure():
    """MIX shrink must stay low-pressure: 10 users / 1000 vectors / fast gen."""
    args = shrink_args(
        "AI-MIX-001",
        Path("C:/MLPerfStorageTest/data/AI-MIX-001"),
        Path("C:/MLPerfStorageTest/results/AI-MIX-001"),
        "32GB",
        pressure=False,
    )
    assert "--num-users" in args and args[args.index("--num-users") + 1] == "10"
    assert "--num-vectors" in args and args[args.index("--num-vectors") + 1] == "1000"
    assert "--generation-mode" in args and args[args.index("--generation-mode") + 1] == "fast"


def test_mix_shrink_args_vdb_on_secondary_drive():
    """With vdb_data_dir the MIX VDB data (milvus db) must land on E:."""
    args = shrink_args(
        "AI-MIX-001",
        Path("C:/MLPerfStorageTest/data/AI-MIX-001"),
        Path("C:/MLPerfStorageTest/results/AI-MIX-001"),
        "32GB",
        pressure=False,
        vdb_data_dir=Path("E:/MLPerfStorageTest/data"),
    )
    mi = args.index("--milvus-uri")
    assert args[mi + 1].replace("\\", "/").startswith("E:/MLPerfStorageTest/data")


def test_catalog_json_valid():
    """Catalog stays valid JSON and MIX family is the 5th family."""
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    families = {c["family"] for c in data}
    assert "MIX" in families
    assert case_family("AI-MIX-001") == "MIX"


def test_gen_case_scripts_mix_cmd_uses_vdb_data_dir(tmp_path):
    """The generated AI-MIX-001.cmd must define VDB_DATA_DIR on the secondary
    drive (E:) and point --milvus-uri / --mix-vdb-data-dir at it, so KV (C:)
    and VectorDB (E:) stay on separate drives."""
    import subprocess
    import sys as _sys

    out_dir = tmp_path / "cases"
    # Regenerate into a temp dir by monkeypatching the module constant is
    # invasive; instead run the generator and check the real output, which
    # is deterministic from the catalog.
    completed = subprocess.run(
        [_sys.executable, str(REPO / "tools" / "gen_case_scripts.py")],
        cwd=REPO, capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    cmd_path = REPO / "scripts" / "cases" / "AI-MIX-001.cmd"
    text = cmd_path.read_text(encoding="utf-8")
    assert 'set "VDB_DATA_DIR=E:\MLPerfStorageTest\data\AI-MIX-001"' in text
    assert "--milvus-uri %VDB_DATA_DIR%\milvus_lite.db" in text
    assert "--mix-vdb-data-dir %VDB_DATA_DIR%" in text


def test_shrink_ckp_write_zero_for_small_disk():
    """ckp_write=0 must force zero-I/O checkpoint (write 0/read 0) so a
    <70GB disk can run link verification without a 105GB llama3-8b write."""
    from full_test_plan_cases.shrink import shrink_args
    args = shrink_args("AI-CKP-001", Path("C:/x"), Path("C:/y"), "64GB",
                       pressure=False, ckp_write=0)
    wi = args.index("--num-checkpoints-write")
    assert args[wi + 1] == "0"
    ri = args.index("--num-checkpoints-read")
    assert args[ri + 1] == "0"


def test_shrink_ckp_write_default_still_real_io():
    """Default ckp_write=None keeps the real-I/O 1/1 smoke."""
    from full_test_plan_cases.shrink import shrink_args
    args = shrink_args("AI-CKP-001", Path("C:/x"), Path("C:/y"), "64GB",
                       pressure=False, ckp_write=None)
    wi = args.index("--num-checkpoints-write")
    assert args[wi + 1] == "1"
    ri = args.index("--num-checkpoints-read")
    assert args[ri + 1] == "1"
