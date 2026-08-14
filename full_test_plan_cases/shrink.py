"""Shared dev-shrink parameter logic for AI SSD cases.

Single source of truth used by:
  * ``scripts/run_ai_ssd_suite.py`` — batch suite runner
  * ``tools/gen_case_scripts.py`` — one-click ``scripts/cases/*.cmd`` generator

Every case shrinks to the smallest practical workload so it fits a 512 GB
disk and finishes well inside the 1.5 h per-case budget (KV Cache is the
slowest at ~10 min; everything else is <= 5 min).
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CATALOG = REPO / "full_test_plan_cases" / "case_catalog.json"
# Repository-root-relative path (NOT absolute): the suite runs with cwd=REPO
# and the .cmd generator rewrites it to %REPO_ROOT%\, so the config resolves
# on any machine regardless of where the repo was cloned.
VDB_SMOKE_REL = "full_test_plan_cases/configs/vdb_smoke.yaml"

CAPACITY_SUFFIXES = ("-1TB", "-2TB", "-4TB")
MEMORY_TIERS = ("32GB", "64GB", "128GB")

# Cases that cannot run on a Windows + Milvus-Lite machine by design.
SKIP_REASONS = {
    "AI-VDB-005": "AISAQ index requires a full Milvus server (Milvus Lite: unknown index_type 'AISAQ')",
}


def base_case_id(case_id: str) -> str:
    """Strip the capacity-tier suffix so family lookup works for -1TB/-2TB/-4TB ids."""
    for suffix in CAPACITY_SUFFIXES:
        if case_id.endswith(suffix):
            return case_id[: -len(suffix)]
    return case_id


def case_family(case_id: str) -> str:
    with open(CATALOG, encoding="utf-8") as fh:
        catalog = json.load(fh)
    for c in catalog:
        if c["case_id"] == base_case_id(case_id):
            return c.get("family", "")
    return ""


def memory_gb(memory: str) -> int:
    """'64GB' -> 64."""
    return int(memory.removesuffix("GB"))


def memory_override_args(family: str, memory: str) -> list[str]:
    """run_case dev flags that set the memory tier for a family.

    Training/Checkpoint use --client-host-memory-in-gb (via run_case
    --client-memory-gb); KV Cache uses its own --cpu-mem-gb tier; VectorDB
    has no client-memory parameter (data lives in the DB engine).
    """
    mb = memory_gb(memory)
    if family in ("Training", "Checkpoint"):
        return ["--client-memory-gb", str(mb)]
    if family == "KV Cache":
        return ["--cpu-mem-gb", str(mb)]
    return []


def shrink_args(case_id: str, data_dir: Path, results_dir: Path, memory: str = "64GB",
                pressure: bool = False) -> list[str]:
    """Build the dev-shrink run_case flags for a case.

    ``pressure=False`` (default): smallest practical workload — pure link
    verification on any disk.  ``pressure=True``: ~10-50x the I/O so the
    SSD is actually exercised (steady-state writes, small-file IOPS,
    sustained KV spill) while still fitting a 512 GB disk inside the
    1.5 h per-case budget.
    """
    family = case_family(case_id)
    base = base_case_id(case_id)
    args: list[str] = []
    if family == "Training":
        if pressure:
            # Per-model file counts sized for ~40-120 GB writes on a 512 GB disk.
            n = {"AI-TRN-003": 300, "AI-TRN-004": 2000, "AI-TRN-005": 2000,
                 "AI-TRN-DLRM": 100}.get(base, 200)
            args += ["--num-files-train", str(n), "--allow-invalid-params"]
        else:
            args += ["--num-files-train", "8", "--allow-invalid-params"]
        if "DLRM" in case_id:
            # Windows + DLIO/parquet: MPI finalize aborts after the run body
            # (data read + metrics already produced); single exec avoids it.
            args += ["--exec-type", "single"]
    elif family == "Checkpoint":
        args += ["--num-processes", "8", "--allow-invalid-params"]
        if base == case_id:
            # Base (512GB) cases: real-I/O smoke. Pressure mode triples the
            # checkpoint count (~340 GB write + read for 70b-class shards).
            w = 3 if pressure else 1
            args += ["--num-checkpoints-write", str(w), "--num-checkpoints-read", str(w)]
    elif family == "KV Cache":
        if pressure:
            args += ["--num-users", "50", "--duration-sec", "60", "--trials", "2",
                     "--inter-option-delay", "5", "--generation-mode", "fast"]
        else:
            args += ["--num-users", "10", "--duration-sec", "10",
                     "--trials", "1", "--inter-option-delay", "0",
                     "--generation-mode", "fast"]
    elif family == "VectorDB":
        args += ["--num-vectors", "10000" if pressure else "100",
                 "--duration-sec", "60" if pressure else "10",
                 "--vdb-config", VDB_SMOKE_REL,
                 "--milvus-uri", str(data_dir / "milvus_lite.db")]
    args += memory_override_args(family, memory)
    return args
