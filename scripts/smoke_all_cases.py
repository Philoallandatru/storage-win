"""Batch smoke-run every native case with shrunk parameters.

Goal: verify each case script can start and complete without errors on the
current machine, using the smallest practical workload:

  Training  -> 8 files + --allow-invalid-params (real datagen + training)
  Checkpoint-> 0 writes / 0 reads + --allow-invalid-params (zero-I/O smoke)
  KV Cache  -> 10s duration, 1 trial, no inter-option delay
  VectorDB  -> BLOCKED here: needs a Milvus server (127.0.0.1:19530)

Usage:
    python scripts/smoke_all_cases.py [--only AI-TRN-003,AI-KV-001]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
PY = REPO / ".venv" / "Scripts" / "python.exe"

DATA_ROOT = Path("D:/mlps_smoke")
RES_ROOT = Path("E:/mlps_smoke_res")


def shrink_args(case: dict) -> list[str] | None:
    family = case["family"]
    if family == "Training":
        return ["--num-files-train", "8", "--allow-invalid-params"]
    if family == "Checkpoint":
        # 8 ranks keeps MPI startup light (70B/405B/1T full runs use 64/512/1024);
        # 0 writes/0 reads is a zero-I/O smoke that still exercises the full CLI path.
        return ["--num-processes", "8", "--num-checkpoints-write", "0", "--num-checkpoints-read", "0", "--allow-invalid-params"]
    if family == "KV Cache":
        return ["--duration-sec", "10", "--trials", "1", "--inter-option-delay", "0"]
    if family == "VectorDB":
        return None  # requires a Milvus server on 127.0.0.1:19530
    return []


def main() -> int:
    from full_test_plan_cases.catalog import load_catalog

    parser = argparse.ArgumentParser(description="Smoke-run every native case with shrunk params")
    parser.add_argument("--only", help="Comma-separated case IDs to run instead of all")
    parser.add_argument("--data-root", type=Path, default=DATA_ROOT)
    parser.add_argument("--results-root", type=Path, default=RES_ROOT)
    args = parser.parse_args()

    only = {c.strip().upper() for c in args.only.split(",")} if args.only else None
    results: list[tuple[str, str, str]] = []
    for case in load_catalog():
        cid = case["case_id"]
        if only and cid not in only:
            continue
        extra = shrink_args(case)
        if extra is None:
            results.append((cid, "BLOCKED", "needs Milvus server (127.0.0.1:19530)"))
            print(f"{cid:12s} BLOCKED  needs Milvus server", flush=True)
            continue
        data_dir = args.data_root / cid
        res_dir = args.results_root / cid
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "checkpoint" / cid).mkdir(parents=True, exist_ok=True)
        command = [
            str(PY), "-m", "full_test_plan_cases.run_case", cid,
            "--data-dir", str(data_dir), "--results-dir", str(res_dir), *extra,
        ]
        started = time.time()
        try:
            completed = subprocess.run(
                command, cwd=REPO, capture_output=True, text=True,
                encoding="utf-8", errors="replace", check=False, timeout=1800,
            )
            rc = completed.returncode
        except subprocess.TimeoutExpired:
            rc = 124
        elapsed = int(time.time() - started)
        status = "PASS" if rc == 0 else "FAIL"
        results.append((cid, status, f"rc={rc} {elapsed}s"))
        print(f"{cid:12s} {status:5s} rc={rc} {elapsed}s", flush=True)

    print("\n== SUMMARY ==")
    for cid, status, note in results:
        print(f"{cid:12s} {status:8s} {note}")
    passed = sum(1 for _, s, _ in results if s == "PASS")
    print(f"\n{passed}/{len(results)} pass; {sum(1 for _, s, _ in results if s == 'BLOCKED')} blocked (env)")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
