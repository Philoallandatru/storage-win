"""Run plan/preflight mode for a selected FULL_TEST_PLAN set."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from full_test_plan_cases.catalog import load_catalog


CASE_DIR = _REPO_ROOT / "full_test_plan_cases" / "cases"


def _case_filename(case_id: str) -> str:
    return f"test_{case_id.lower().replace('-', '_')}.py"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all matching FULL_TEST_PLAN case entrypoints")
    parser.add_argument("--mode", choices=("plan", "preflight", "dry-run", "execute"), default="plan")
    parser.add_argument("--family")
    parser.add_argument("--priority", choices=("P0", "P1", "P2"))
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--results-dir", default="results/full_test_plan")
    parser.add_argument("--launcher", choices=("single", "mpi"), default="single")
    parser.add_argument("--mpi-bin", choices=("mpiexec", "mpirun"), default="mpiexec" if os.name == "nt" else "mpirun")
    parser.add_argument("--mlpstorage", type=Path)
    parser.add_argument("--repeats", type=int)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--accelerators", type=int)
    parser.add_argument("--client-memory-gb", type=int)
    parser.add_argument("--duration-sec", type=int)
    parser.add_argument("--query-processes", type=int)
    parser.add_argument("--systemname")
    parser.add_argument("--dlio-bin-path", type=Path)
    parser.add_argument("--o-direct", action="store_true")
    parser.add_argument("--confirm-dut", action="store_true")
    parser.add_argument("--init-results", action="store_true")
    parser.add_argument("--cleanup-data", action="store_true")
    parser.add_argument("--cleanup-root", type=Path)
    args = parser.parse_args()
    selected = [
        case for case in load_catalog()
        if (not args.family or case["family"].lower() == args.family.lower())
        and (not args.priority or case["priority"] == args.priority)
    ]
    failures = 0
    common_args = [
        "--mode", args.mode,
        "--data-dir", str(args.data_dir),
        "--results-dir", str(args.results_dir),
        "--launcher", args.launcher,
        "--mpi-bin", args.mpi_bin,
    ]
    if args.confirm_dut:
        common_args.append("--confirm-dut")
    for flag, value in (
        ("--mlpstorage", args.mlpstorage),
        ("--loops", args.repeats),
        ("--duration-sec", args.duration_sec),
        ("--accelerators", args.accelerators),
        ("--client-memory-gb", args.client_memory_gb),
        ("--query-processes", args.query_processes),
        ("--systemname", args.systemname),
        ("--dlio-bin-path", args.dlio_bin_path),
    ):
        if value is not None:
            common_args.extend([flag, str(value)])
    for flag, enabled in (("--prepare", args.prepare), ("--o-direct", args.o_direct)):
        if enabled:
            common_args.append(flag)
    for flag, enabled in (("--init-results", args.init_results), ("--cleanup-data", args.cleanup_data)):
        if enabled:
            common_args.append(flag)
    if args.cleanup_root is not None:
        common_args.extend(["--cleanup-root", str(args.cleanup_root)])
    for case in selected:
        command = [
            sys.executable,
            str(CASE_DIR / _case_filename(case["case_id"])),
            *common_args,
        ]
        completed = subprocess.run(command, cwd=_REPO_ROOT, check=False)
        if completed.returncode != 0:
            failures += 1
            # Plan mode is an inventory operation: list every native blocker.
            # All executable modes are suite-level fast-fail by design.
            if args.mode != "plan":
                break
    print(f"selected={len(selected)} failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
