"""Shared infrastructure for the 16 AI SSD Training case wrappers.

This module is intentionally small.  It owns three responsibilities:

1. ``build_argparser()`` — the standard argparse surface every
   wrapper exposes.  Flags mirror the inner runner (``tools/...``)
   so an operator familiar with the runner can drop a wrapper in
   without learning a new CLI.

2. ``build_command()`` — translate the argparse result into the
   ``[python, tools/ai_ssd_training_case_runner.py, --case, ...]``
   command the inner runner expects.  The wrapper injects ``--execute``
   unconditionally (the inner runner rejects without it) and the
   per-case flags the runner needs.

3. ``main(case_id, info)`` — the run loop: validate the layout
   (data-dir and result-dir must not overlap), pre-pend the venv's
   ``Scripts`` directory to ``PATH`` so ``mlpstorage`` and
   ``dlio_benchmark`` are locatable, launch the subprocess, capture
   stdout/stderr to a log file, write ``manifest.json`` and
   ``verdict.json``, and auto-clean any ``python_scaled/`` subtree
   the case produced (unless ``--keep-data`` is passed).

The 16 case files in this directory each call ``main(case_id, INFO)``
with a frozen ``INFO`` dict that records the case-specific rationale.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_RUNNER = REPO_ROOT / "tools" / "ai_ssd_training_case_runner.py"


@dataclass(frozen=True)
class CaseInfo:
    case_id: str
    model: str
    accelerator: str
    data_format: str
    execution: str            # native | native_special | python_scaled
    capacity_gib: float       # dataset size (NOT the target SSD)
    destructive: bool
    notes: str                # xlsx row + the wrapper's interpretation


# ``destructive`` mirrors the catalog default; the Training family is
# non-destructive per ai_ssd_test_cases/catalog.py.
DEFAULT_CASES: dict[str, CaseInfo] = {
    "AI-TRN-001": CaseInfo("AI-TRN-001", "unet3d-a100",  "A100",  "npz",      "native_special",  983.0, False, "xlsx row 1; 7,200 files; same dataset as TRN-003 but A100 compute time."),
    "AI-TRN-002": CaseInfo("AI-TRN-002", "unet3d-h100",  "H100",  "npz",      "python_scaled",     22.9, False, "xlsx row 2; 168 files (~22.9 GiB); no current native entry; scaled fallback only."),
    "AI-TRN-003": CaseInfo("AI-TRN-003", "unet3d-b200",  "B200",  "npz",      "native",           983.0, False, "xlsx row 3; 7,200 files (~983 GiB); CAP-01 will BLOCK on a <1 TB DUT."),
    "AI-TRN-004": CaseInfo("AI-TRN-004", "retinanet-b200-jpeg", "B200",  "jpeg",  "native", 351.64, False, "xlsx row 4; 1.17M JPEG files (RetinaNet B200); Windows fork is the first blocker once data is generated."),
    "AI-TRN-005": CaseInfo("AI-TRN-005", "retinanet-mi355-jpeg","MI355", "jpeg",  "native", 351.64, False, "xlsx row 5; same dataset as TRN-004 with MI355 compute time; not blocked by missing GPU."),
    "AI-TRN-006": CaseInfo("AI-TRN-006", "cosmoflow-a100-tfrecord","A100", "tfrecord", "python_scaled", 1.0, False, "xlsx row 6; CosmoFlow TFRecord; only Python-scaled fallback is implemented."),
    "AI-TRN-007": CaseInfo("AI-TRN-007", "cosmoflow-h100-tfrecord","H100", "tfrecord", "python_scaled", 1.0, False, "xlsx row 7; CosmoFlow TFRecord; shuffle / read_threads sweep not supported by the scaled harness."),
    "AI-TRN-008": CaseInfo("AI-TRN-008", "resnet50-a100-tfrecord", "A100", "tfrecord", "python_scaled", 1.0, False, "xlsx row 8; ResNet50 TFRecord; multi-sample per file not reproduced by the scaled harness."),
    "AI-TRN-009": CaseInfo("AI-TRN-009", "resnet50-h100-tfrecord", "H100", "tfrecord", "python_scaled", 1.0, False, "xlsx row 9; ResNet50 TFRecord; higher-workers sweep not supported by the scaled harness."),
    "AI-TRN-010": CaseInfo("AI-TRN-010", "dlrm-b200-parquet",      "B200", "parquet",  "python_scaled", 1.0, False, "xlsx row 10; DLRM Parquet; prefetch sweep not supported by the scaled harness."),
    "AI-TRN-011": CaseInfo("AI-TRN-011", "dlrm-mi355-parquet",     "MI355","parquet",  "python_scaled", 1.0, False, "xlsx row 11; DLRM Parquet; read_threads sweep not supported by the scaled harness."),
    "AI-TRN-012": CaseInfo("AI-TRN-012", "flux-b200-parquet",      "B200", "parquet",  "python_scaled", 1.0, False, "xlsx row 12; Flux large Parquet; sustained BW needs a real DLIO run, not the Python scaled loop."),
    "AI-TRN-013": CaseInfo("AI-TRN-013", "flux-mi355-parquet",     "MI355","parquet",  "python_scaled", 1.0, False, "xlsx row 13; Flux Parquet; burst-after-long-compute-gap not reproducible in the scaled harness."),
    "AI-TRN-014": CaseInfo("AI-TRN-014", "training-concurrency",   "*",    "mixed",    "python_scaled", 1.0, False, "xlsx row 14; workers 1..16 sweep is not in the Python scaled harness; wrapper is a single-point run."),
    "AI-TRN-015": CaseInfo("AI-TRN-015", "read-threads-saturation","*",    "mixed",    "python_scaled", 1.0, False, "xlsx row 15; read_threads 1..32 sweep is not in the scaled harness; wrapper is a single-point run."),
    "AI-TRN-016": CaseInfo("AI-TRN-016", "warm-cold-direct",       "*",    "mixed",    "python_scaled", 1.0, False, "xlsx row 16; warm/cold/direct three-way comparison is not in the scaled harness; wrapper runs the buffered path only."),
}


def build_argparser(case_id: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=f"Run {case_id} (Training case wrapper)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--data-dir", type=Path, required=True, help="DUT data directory.")
    p.add_argument("--result-dir", type=Path, required=True, help="Result directory; must NOT be inside --data-dir.")
    p.add_argument("--duration-sec", type=int, default=300, help="Per-run duration passed to the inner runner.")
    p.add_argument("--repeat", type=int, default=3, help="Number of repetitions; 0 means 'do not loop'.")
    p.add_argument("--scale-mb", type=int, default=1024,
                   help="Synthetic data size for python_scaled cases; required by the inner runner.")
    p.add_argument("--prepare", action="store_true", help="Run native datagen before the workload (native cases only).")
    p.add_argument("--confirm-dut", action="store_true", help="Confirm the DUT path; required for destructive cases.")
    p.add_argument("--keep-data", action="store_true", help="Do NOT auto-clean the python_scaled/ subtree on exit.")
    p.add_argument("--timeout-sec", type=float, default=90.0,
                   help="Hard wall-clock kill switch for the inner subprocess.")
    p.add_argument("--dry-run", action="store_true", help="Print the command that would run but do not execute it.")
    return p


def build_command(case_id: str, args: argparse.Namespace, python: Path) -> list[str]:
    cmd: list[str] = [
        str(python),
        str(TOOLS_RUNNER),
        "--case", case_id,
        "--execute",
        "--data-dir", str(args.data_dir.resolve()),
        "--result-dir", str(args.result_dir.resolve()),
        "--duration-sec", str(args.duration_sec),
        "--repeat", str(args.repeat),
        "--users", "25",
        "--launcher", "single",
        "--mpi-bin", "mpiexec",
        "--client-memory-gb", "64",
        "--accelerators", "1",
    ]
    if args.prepare:
        cmd.append("--prepare")
    if args.confirm_dut:
        cmd.append("--confirm-dut")
    if args.scale_mb is not None:
        cmd += ["--scale-mb", str(args.scale_mb)]
    if args.keep_data:
        cmd.append("--keep-data")
    return cmd


def _validate_layout(data_dir: Path, result_dir: Path) -> list[str]:
    issues: list[str] = []
    if os.name != "nt":
        issues.append("this wrapper targets native Windows; WSL is not supported")
    if not data_dir.exists():
        issues.append(f"--data-dir does not exist: {data_dir}")
    if data_dir == result_dir or str(result_dir).startswith(str(data_dir) + os.sep):
        issues.append("--result-dir must not be inside --data-dir")
    return issues


def _now_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(case_id: str, info: CaseInfo, argv: Sequence[str] | None = None) -> int:
    if case_id not in DEFAULT_CASES:
        print(f"unknown case id: {case_id!r}", file=sys.stderr)
        return 2
    args = build_argparser(case_id).parse_args(list(argv) if argv is not None else None)

    data_dir = args.data_dir.resolve()
    result_dir = args.result_dir.resolve()
    layout_issues = _validate_layout(data_dir, result_dir)
    if layout_issues:
        for issue in layout_issues:
            print(f"BLOCKED: {issue}", file=sys.stderr)
        return 2

    if info.execution == "python_scaled" and args.scale_mb is None:
        print(
            f"WARNING: {case_id} is python_scaled; the inner runner rejects "
            f"without --scale-mb. Pass --scale-mb <positive-int> to enable it.",
            file=sys.stderr,
        )

    python = Path(sys.executable)
    cmd = build_command(case_id, args, python)

    if args.dry_run:
        print(subprocess.list2cmdline(cmd))
        return 0

    run_dir = result_dir / case_id / _now_run_id()
    run_dir.mkdir(parents=True, exist_ok=True)

    # Inject the active venv's Scripts directory into PATH so the inner
    # runner can find mlpstorage.exe and dlio_benchmark.exe without an
    # external PATH setup.
    env = os.environ.copy()
    env["PATH"] = str(python.parent) + os.pathsep + env.get("PATH", "")

    manifest: dict = {
        "case_id": case_id,
        "model": info.model,
        "accelerator": info.accelerator,
        "data_format": info.data_format,
        "execution": info.execution,
        "capacity_gib": info.capacity_gib,
        "destructive": info.destructive,
        "notes": info.notes,
        "argv": list(argv) if argv is not None else sys.argv[1:],
        "command": cmd,
        "timeout_sec": args.timeout_sec,
        "host": {"platform": platform.platform(), "python": str(python)},
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    started = time.perf_counter()
    try:
        completed = subprocess.run(
            cmd, check=False, timeout=args.timeout_sec,
            capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
        )
        rc = completed.returncode
        (run_dir / "wrapper_stdout.log").write_text(completed.stdout or "", encoding="utf-8")
        (run_dir / "wrapper_stderr.log").write_text(completed.stderr or "", encoding="utf-8")
    except subprocess.TimeoutExpired:
        rc = 124
        (run_dir / "wrapper_timeout.txt").write_text(
            f"timeout after {args.timeout_sec}s\n", encoding="utf-8"
        )
    elapsed = time.perf_counter() - started

    manifest["elapsed_seconds"] = round(elapsed, 3)
    manifest["returncode"] = rc
    manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
    if rc == 124:
        manifest["status"] = "TIMEOUT"
        manifest["formal_status"] = "TIMEOUT"
    elif rc == 0:
        manifest["status"] = "PASS"
        manifest["formal_status"] = "FORMAL" if info.execution in {"native", "native_special"} else "NOT_FORMAL"
    elif rc == 2:
        manifest["status"] = "BLOCKED"
        manifest["formal_status"] = "BLOCKED"
    else:
        manifest["status"] = "FAIL"
        manifest["formal_status"] = "EXPECTED_FAIL" if info.execution in {"native", "native_special"} else "NOT_FORMAL"

    # python_scaled cases are self-contained — remove the python_scaled/
    # subtree we generated so the host disk returns to its pre-run state.
    cleanup: dict = {"executed": False, "scope": None, "files": 0, "bytes": 0}
    if info.execution == "python_scaled" and not args.keep_data:
        sub = data_dir / "python_scaled"
        if sub.exists():
            files = sum(1 for _ in sub.rglob("*") if _.is_file())
            size = sum(_.stat().st_size for _ in sub.rglob("*") if _.is_file())
            import shutil
            shutil.rmtree(sub, ignore_errors=True)
            cleanup = {
                "executed": True,
                "scope": str(sub),
                "files": files,
                "bytes": size,
            }
    manifest["cleanup"] = cleanup

    _write_json(run_dir / "manifest.json", manifest)
    _write_json(run_dir / "verdict.json", manifest)
    print(f"manifest -> {run_dir / 'manifest.json'}")
    return rc
