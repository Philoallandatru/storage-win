"""Resolve mlpstorage argv for a native FULL_TEST_PLAN case.

Reads the case entrypoint's COMMANDS list, applies the case's own
placeholder substitution table, and prints the resolved commands as
JSON on stdout. The case files (test_ai_*.py) are the single source
of truth — this script mirrors the values-dict each case file
builds in its main() so the runner doesn't have to re-implement
placeholder logic for every case family.

Usage:
    python _resolve_case_args.py <case_file> <data_dir> <results_dir> \\
        --systemname <id> --loops N --mpi-bin <bin> \\
        --num-accelerators N --client-memory-gb N \\
        --duration-sec N --query-processes N --num-users N \\
        --gpu-mem-gb N --cpu-mem-gb N --accelerator-type <type> \\
        --skip-fs-separation-gate --dry-run \\
        --params K=V [--params K=V ...]

Output: JSON document with shape
    {"case_id": ..., "native_status": ..., "native_reason": ...,
     "commands": [{"phase": ..., "argv": [...]}, ...]}
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("case_file", type=Path)
    p.add_argument("data_dir", type=Path)
    p.add_argument("results_dir", type=Path)
    p.add_argument("--systemname", required=True)
    p.add_argument("--loops", type=int, default=1)
    p.add_argument("--mpi-bin", default="mpiexec")
    p.add_argument("--num-accelerators", type=int, default=1)
    p.add_argument("--client-memory-gb", type=int, default=64)
    p.add_argument("--duration-sec", type=int, default=60)
    p.add_argument("--query-processes", type=int, default=1)
    p.add_argument("--num-users", type=int, default=200)
    p.add_argument("--gpu-mem-gb", type=int, default=0)
    p.add_argument("--cpu-mem-gb", type=int, default=0)
    p.add_argument("--accelerator-type", default="h100")
    p.add_argument("--skip-fs-separation-gate", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--params", action="append", default=[])
    return p


def main() -> int:
    args = build_argparser().parse_args()
    if not args.case_file.is_file():
        print(f"case file not found: {args.case_file}", file=sys.stderr)
        return 2

    spec = importlib.util.spec_from_file_location("case_mod", args.case_file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    case_id = getattr(mod, "CASE_ID", args.case_file.stem.replace("test_", ""))
    native_status = getattr(mod, "NATIVE_STATUS", "UNKNOWN")
    native_reason = getattr(mod, "NATIVE_REASON", None)
    raw_cmds = getattr(mod, "COMMANDS", []) or []

    data_dir = args.data_dir.resolve()
    results_dir = args.results_dir.resolve()
    values = {
        "<DATA_DIR>": str(data_dir),
        "<RESULTS_DIR>": str(results_dir),
        "<CHECKPOINT_DIR>": str(data_dir / "checkpoint" / case_id),
        "<CACHE_DIR>": str(data_dir / "kvcache" / case_id),
        "<STORAGE_ROOT>": str(data_dir / "milvus" / case_id),
        "<DUT_DIR>": str(data_dir),
        "<DUT_DATA>": str(data_dir),
        "<SYSTEMNAME>": args.systemname,
        "<LOOPS>": str(args.loops),
        "<MPI_BIN>": args.mpi_bin,
        "<ACCELERATORS>": str(args.num_accelerators),
        "<NUM_ACCELERATORS>": str(args.num_accelerators),
        "<CLIENT_MEMORY_GB>": str(args.client_memory_gb),
        "<DURATION_SEC>": str(args.duration_sec),
        "<QUERY_PROCESSES>": str(args.query_processes),
        "<USERS>": str(args.num_users),
        "<NUM_USERS>": str(args.num_users),
        "<GPU_TIER_GB>": str(args.gpu_mem_gb),
        "<GPU_MEM_GB>": str(args.gpu_mem_gb),
        "<CPU_TIER_GB>": str(args.cpu_mem_gb),
        "<CPU_MEM_GB>": str(args.cpu_mem_gb),
        "<RESULT_DIR>": str(results_dir),
    }

    resolved = []
    for c in raw_cmds:
        argv = []
        for tok in c["argv"]:
            if isinstance(tok, str) and tok in values:
                argv.append(values[tok])
            else:
                argv.append(tok)
        resolved.append({"phase": c["phase"], "argv": argv})

    # Inject --accelerator-type on TRN/CKP run phases if missing.
    for c in resolved:
        if c["phase"] == "run" and any(
            k in c["argv"] for k in ("training", "checkpointing")
        ) and "--accelerator-type" not in c["argv"]:
            c["argv"] += ["--accelerator-type", args.accelerator_type]

    # Family-wide flags — apply once at the end of every phase that
    # doesn't already have them. Param values get injected via --params.
    extras: list[str] = []
    if args.skip_fs_separation_gate:
        extras.append("--skip-fs-separation-gate")
    if args.dry_run:
        extras.append("--dry-run")
    if args.params and not any("--params" in c["argv"] for c in resolved):
        extras += ["--params", *args.params]
    if extras:
        for c in resolved:
            c["argv"] += [e for e in extras if e not in c["argv"]]

    out = {
        "case_id": case_id,
        "native_status": native_status,
        "native_reason": native_reason,
        "commands": resolved,
    }
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
