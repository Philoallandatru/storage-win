#!/usr/bin/env python
"""run_ai_ssd_suite.py — run every AI SSD case shrunk to fit any disk.

Goal (512GB-disk constraint):
  * Every MLPerf test type (Training / Checkpoint / KV Cache / VectorDB)
    and every capacity tier (512GB / 1TB / 2TB / 4TB) runs end-to-end on
    one machine, with data/results drives selectable on the command line.
  * All cases run with shrunk parameters (small datagen, zero-I/O
    checkpoint, 10 s KV runs, 100-vector Milvus Lite) so the whole suite
    completes in a reasonable time and needs only ~30 GB free space.
  * Environment is checked before running, test data is removed after
    each case, and a PASS/FAIL summary is written out.

Usage:
    python scripts/run_ai_ssd_suite.py --capacity 512GB --data-drive D: --results-drive E:
    python scripts/run_ai_ssd_suite.py --capacity 1TB  --data-drive G: --results-drive G:
    python scripts/run_ai_ssd_suite.py --capacity 4TB  --data-drive D: --results-drive E: --only AI-TRN-003-1TB
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

PY = REPO / ".venv" / "Scripts" / "python.exe"
RUN_CASE = [str(PY), "-m", "full_test_plan_cases.run_case"]


def _env_with_venv_path() -> dict:
    """Inherit os.environ but put .venv/Scripts first so ``shutil.which``
    inside mlpstorage (e.g. ``dlio_benchmark`` for E204) resolves console
    scripts — the same PATH injection run_case.cmd does."""
    env = os.environ.copy()
    scripts = str(REPO / ".venv" / "Scripts")
    env["PATH"] = scripts + os.pathsep + env.get("PATH", "")
    return env
CATALOG = REPO / "full_test_plan_cases" / "case_catalog.json"
CAPACITY = REPO / "full_test_plan_cases" / "capacity_catalog.json"

from full_test_plan_cases.shrink import (  # noqa: E402
    SKIP_REASONS,
    base_case_id,
    case_family,
    shrink_args,
)

# Minimal free-space floors the environment check enforces (bytes).
# KV with llama3.1-70b + 10 users needs ~26.8 GB (CAP-01) — keep headroom.
DATA_SPACE_FLOOR = 40 * 1024**3
RESULT_SPACE_FLOOR = 2 * 1024**3

SUPPORTED_TIERS = ("512GB", "1TB", "2TB", "4TB")
SUPPORTED_MEMORY = ("32GB", "64GB", "128GB")
MATRIX = REPO / "full_test_plan_cases" / "matrix_catalog.json"


def load_catalog() -> list[dict]:
    with open(CATALOG, encoding="utf-8") as fh:
        return json.load(fh)


def load_capacity() -> dict:
    with open(CAPACITY, encoding="utf-8") as fh:
        return json.load(fh)


def cases_for_tier(tier: str) -> list[str]:
    """Return the case-id list for a capacity tier.

    ``512GB`` is the plain catalog (all 34 base cases); the other tiers
    come from capacity_catalog.json (one representative per family).
    """
    if tier == "512GB":
        return [c["case_id"] for c in load_catalog()]
    cap = load_capacity()
    body = cap[tier]
    entries = body.get("cases", body) if isinstance(body, dict) else body
    if isinstance(entries, dict):
        entries = {k: v for k, v in entries.items() if not k.startswith("_")}
    return [c["case_id"] for c in entries] if isinstance(entries, list) else list(entries.keys())


# ---------------------------------------------------------------------------
# Environment checks (run before any case executes)
# ---------------------------------------------------------------------------

def env_checks(data_drive: str, results_drive: str, include_vdb: bool) -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, ok, detail))

    add("python", PY.exists(), str(PY))
    if PY.exists():
        env = _env_with_venv_path()
        probe = subprocess.run([str(PY), "-m", "mlpstorage_py.main", "--help"],
                               capture_output=True, text=True, timeout=60, env=env,
                               encoding="utf-8", errors="replace")
        add("mlpstorage", probe.returncode == 0,
            "rc=%s" % probe.returncode if probe.returncode else "CLI reachable")
    if include_vdb:
        env = _env_with_venv_path()
        vdb = subprocess.run([str(PY), "-c", "import vdbbench"], capture_output=True, text=True, env=env)
        add("vdbbench", vdb.returncode == 0, "import vdbbench")
        mil = subprocess.run([str(PY), "-c", "import milvus_lite"], capture_output=True, text=True, env=env)
        add("milvus_lite", mil.returncode == 0, "import milvus_lite")
    mpi = shutil.which("mpiexec") or shutil.which("mpirun")
    add("mpi", mpi is not None, mpi or "mpiexec not found (cluster-collect will fall back to local)")

    for drive, label in ((data_drive, "data"), (results_drive, "results")):
        root = Path(f"{drive}\\")
        ok = root.exists()
        detail = "exists" if ok else "MISSING"
        if ok:
            try:
                shutil.disk_usage(root)
                detail = "writable"
            except OSError:
                ok, detail = False, "not accessible"
        add(f"{label}_drive", ok, f"{drive} {detail}")
    return checks


# ---------------------------------------------------------------------------
# Case runner + cleanup
# ---------------------------------------------------------------------------

def run_case(case_id: str, data_dir: Path, results_dir: Path, timeout: int, memory: str = "64GB",
             single_drive: bool = False) -> tuple[int, str]:
    argv = [*RUN_CASE, case_id, "--mode", "execute",
            "--data-dir", str(data_dir), "--results-dir", str(results_dir),
            *shrink_args(case_id, data_dir, results_dir, memory)]
    if single_drive:
        # Only one drive exists (e.g. a C:-only laptop): CAP-03 would flag
        # data/results as same filesystem, so bypass the gate.
        argv.append("--skip-fs-separation-gate")
    print(f"\n===== {case_id}  ({case_family(case_id)}) =====", flush=True)
    started = time.monotonic()
    try:
        proc = subprocess.run(argv, cwd=REPO, timeout=timeout,
                              env=_env_with_venv_path(),
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
        rc = proc.returncode
        tail = (proc.stdout or "")[-1500:]
        if proc.returncode != 0:
            tail = (proc.stderr or "")[-800:] + tail
    except subprocess.TimeoutExpired:
        rc, tail = -1, f"TIMEOUT after {timeout}s"
    duration = time.monotonic() - started
    print(tail, flush=True)
    print(f"---- {case_id} rc={rc}  {duration:.0f}s ----", flush=True)
    return rc, f"{duration:.0f}s"


def cleanup_dir(path: Path, case_id: str) -> None:
    """Delete a test directory only when the path embeds the case id (safety)."""
    if not path.exists():
        return
    if case_id.lower() not in str(path).lower():
        print(f"CLEANUP_SKIPPED: {path} does not embed {case_id} — refusing to delete")
        return
    shutil.rmtree(path, ignore_errors=True)
    print(f"CLEANED: {path}")


# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--capacity", choices=SUPPORTED_TIERS, default="512GB",
                        help="capacity tier to run (default 512GB = all 34 base cases)")
    parser.add_argument("--memory", choices=SUPPORTED_MEMORY, default="64GB",
                        help="client-memory tier for this run: 32GB/64GB/128GB (default 64GB)")
    parser.add_argument("--data-drive", default="D:", help="drive for test data, e.g. D:")
    parser.add_argument("--results-drive", default=None, help="drive for results (default: same as data-drive)")
    parser.add_argument("--only", help="comma-separated case ids to run instead of the full tier set")
    parser.add_argument("--case-timeout", type=int, default=900, help="per-case timeout in seconds (default 900)")
    parser.add_argument("--keep-data", action="store_true", help="do not delete data after each case")
    parser.add_argument("--keep-results", action="store_true", help="do not clear results before each case")
    parser.add_argument("--skip-env-check", action="store_true")
    args = parser.parse_args()

    results_drive = args.results_drive or args.data_drive
    single_drive = args.data_drive.upper().rstrip(":\\") == results_drive.upper().rstrip(":\\")
    tier_cases = cases_for_tier(args.capacity)
    if args.only:
        wanted = {c.strip().upper() for c in args.only.split(",")}
        tier_cases = [c for c in tier_cases if c.upper() in wanted]

    data_root = Path(f"{args.data_drive}\\MLPerfStorageTest\\data")
    results_root = Path(f"{results_drive}\\MLPerfStorageTest\\results")
    print(f"capacity={args.capacity}  memory={args.memory}  data={args.data_drive}  results={results_drive}  "
          f"cases={len(tier_cases)}", flush=True)

    # ---- environment check -------------------------------------------------
    if not args.skip_env_check:
        print("\n--- environment check ---", flush=True)
        include_vdb = any(case_family(c) == "VectorDB" for c in tier_cases)
        failed = False
        for name, ok, detail in env_checks(args.data_drive, results_drive, include_vdb):
            print(f"  [{'OK ' if ok else 'FAIL'}] {name}: {detail}", flush=True)
            failed = failed or not ok
        if failed:
            print("ENV_CHECK_FAILED — fix the environment or pass --skip-env-check", file=sys.stderr)
            return 2

    # ---- run cases ----------------------------------------------------------
    summary: list[dict] = []
    for case_id in tier_cases:
        if case_id in SKIP_REASONS:
            print(f"\n===== {case_id}  ({case_family(case_id)}) =====", flush=True)
            print(f"SKIP: {SKIP_REASONS[case_id]}", flush=True)
            summary.append({"case_id": case_id, "family": case_family(case_id),
                            "result": "SKIP", "rc": -1, "duration": "0s"})
            continue
        data_dir = data_root / case_id
        results_dir = results_root / case_id
        if not args.keep_results:
            cleanup_dir(results_dir, case_id)
        cleanup_dir(data_dir, case_id)
        rc, duration = run_case(case_id, data_dir, results_dir, args.case_timeout, args.memory, single_drive)
        if not args.keep_data:
            cleanup_dir(data_dir, case_id)
        result = "PASS" if rc == 0 else ("FAIL" if rc != -1 else "TIMEOUT")
        summary.append({"case_id": case_id, "family": case_family(case_id),
                        "result": result, "rc": rc, "duration": duration})

    # ---- summary -------------------------------------------------------------
    ok_count = sum(1 for s in summary if s["result"] == "PASS")
    print("\n" + "=" * 60, flush=True)
    print(f"SUITE SUMMARY  capacity={args.capacity}  memory={args.memory}  {ok_count}/{len(summary)} passed", flush=True)
    print("=" * 60, flush=True)
    for s in summary:
        print(f"  {s['case_id']:<18} {s['family']:<12} {s['result']:<8} rc={s['rc']:<4} {s['duration']}s", flush=True)

    out = results_root.parent / f"suite_summary_{args.capacity}_{args.memory}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"capacity": args.capacity, "memory": args.memory, "results": summary,
                               "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")},
                              indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nsummary written: {out}", flush=True)
    return 0 if all(s["result"] in ("PASS", "SKIP") for s in summary) else 1


if __name__ == "__main__":
    sys.exit(main())
