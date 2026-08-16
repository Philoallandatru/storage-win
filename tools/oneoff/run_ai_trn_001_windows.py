"""Run the AI-TRN-001 A100 workload on native Windows.

This is an AI-PC OPEN workload entrypoint.  It is intentionally separate from
the v3.0 FULL_TEST_PLAN catalog, whose CLOSED training set is B200/MI355.
The formal workload uses the 7,200-file UNet3D dataset (about 983 GiB); a
capacity failure is a valid BLOCKED result, not a reason to silently shrink
the case.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


CASE_ID = "AI-TRN-001"
TRAIN_FILE_COUNT = 7200


def _find_mlpstorage(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit
    for candidate in (
        Path(sys.executable).with_name("mlpstorage.exe"),
        Path(sys.executable).with_name("mlpstorage"),
    ):
        if candidate.is_file():
            return candidate
    return Path(shutil.which("mlpstorage") or "mlpstorage")


def _run(command: list[str], phase: str) -> int:
    print(f"{CASE_ID} {phase}: {subprocess.list2cmdline(command)}", flush=True)
    try:
        completed = subprocess.run(command, check=False)
    except OSError as error:
        print(f"{CASE_ID} FAIL phase={phase}: {error}", file=sys.stderr)
        return 1
    if completed.returncode:
        print(f"{CASE_ID} {phase} failed with exit code {completed.returncode}", file=sys.stderr)
    return completed.returncode


def _cleanup(data_dir: Path, cleanup_root: Path | None) -> bool:
    if cleanup_root is None:
        return True
    data_path = data_dir.resolve()
    root_path = cleanup_root.resolve()
    if data_path == root_path or root_path not in data_path.parents:
        print(f"{CASE_ID} CLEANUP_FAILED: data path is outside cleanup root", file=sys.stderr)
        return False
    if data_path.exists():
        shutil.rmtree(data_path)
    return not data_path.exists()


def main() -> int:
    parser = argparse.ArgumentParser(description=f"{CASE_ID} native Windows A100 workload")
    parser.add_argument("--data-dir", type=Path, default=Path(os.environ.get("DUT_DATA", "data")))
    parser.add_argument("--results-dir", type=Path, default=Path(os.environ.get("MLPERF_RESULTS_DIR", "results")))
    parser.add_argument("--mlpstorage", type=Path)
    parser.add_argument("--mpi-bin", choices=("mpiexec", "mpirun"), default="mpiexec" if os.name == "nt" else "mpirun")
    parser.add_argument("--systemname", default=f"{CASE_ID.lower()}-native")
    parser.add_argument("--client-memory-gb", type=int, default=53)
    parser.add_argument("--accelerators", type=int, default=1)
    parser.add_argument("--loops", type=int, default=1)
    parser.add_argument("--dlio-bin-path", type=Path)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--confirm-dut", action="store_true")
    parser.add_argument("--init-results", action="store_true")
    parser.add_argument("--o-direct", action="store_true")
    parser.add_argument("--cleanup-data", action="store_true")
    parser.add_argument("--cleanup-root", type=Path)
    args = parser.parse_args()

    if os.name != "nt":
        print(f"{CASE_ID} ERROR: this entrypoint requires native Windows", file=sys.stderr)
        return 2
    if not args.confirm_dut:
        print(f"{CASE_ID} ERROR: --confirm-dut is required", file=sys.stderr)
        return 2
    if args.cleanup_data and args.cleanup_root is None:
        print(f"{CASE_ID} ERROR: --cleanup-data requires --cleanup-root", file=sys.stderr)
        return 2

    cli = _find_mlpstorage(args.mlpstorage)
    if not cli.is_file() and shutil.which(str(cli)) is None:
        print(f"{CASE_ID} ERROR: mlpstorage executable not found: {cli}", file=sys.stderr)
        return 2
    venv_scripts = str(Path(sys.executable).resolve().parent)
    os.environ["PATH"] = venv_scripts + os.pathsep + os.environ.get("PATH", "")

    data_dir = args.data_dir.resolve()
    results_dir = args.results_dir.resolve()
    common = [
        "--data-dir", str(data_dir),
        "--results-dir", str(results_dir),
        "--systemname", args.systemname,
        "--exec-type", "mpi",
        "--mpi-bin", args.mpi_bin,
        "--params", f"dataset.num_files_train={TRAIN_FILE_COUNT}",
    ]
    datagen = [
        str(cli), "open", "training", "unet3d", "datagen", "file",
        "--num-processes", "1", *common,
    ]
    run = [
        str(cli), "open", "training", "unet3d", "run", "file",
        "--num-accelerators", str(args.accelerators),
        "--accelerator-type", "a100",
        "--client-host-memory-in-gb", str(args.client_memory_gb),
        "--loops", str(args.loops),
        *common,
    ]
    if args.o_direct:
        run.append("--o-direct")
    if args.dlio_bin_path:
        datagen.extend(["--dlio-bin-path", str(args.dlio_bin_path)])
        run.extend(["--dlio-bin-path", str(args.dlio_bin_path)])

    if args.init_results:
        results_dir.parent.mkdir(parents=True, exist_ok=True)
        code = _run([str(cli), "init", args.systemname, str(results_dir)], "init")
        if code:
            return code

    selected = (
        [("prepare", datagen), ("run", run)]
        if args.prepare
        else [("run", run)]
    )
    for phase, command in selected:
        code = _run(command, phase)
        if code:
            if args.cleanup_data and not _cleanup(data_dir, args.cleanup_root):
                return 1
            return code

    if args.cleanup_data and not _cleanup(data_dir, args.cleanup_root):
        return 1
    print(f"{CASE_ID} PASS (OPEN A100 workload completed; review AU and physical-disk evidence)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
