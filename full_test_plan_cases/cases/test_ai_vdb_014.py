"""FULL_TEST_PLAN Case 065: AI-VDB-014.

The command list below is the native mlpstorage command for this case.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


CASE_ID = 'AI-VDB-014'
NATIVE_STATUS = 'SUPPORTED'
NATIVE_REASON = 'mlpstorage'
COMMANDS = [{'phase': 'prepare', 'argv': ['open', 'vectordb', 'datagen', 'file', '--vdb-engine', 'milvus', '--vdb-index', 'HNSW', '--host', '127.0.0.1', '--port', '19530', '--collection', 'ai_vdb_014_hnsw', '--num-vectors', '1000', '--dimension', '128', '--num-shards', '1', '--force', '--results-dir', '<RESULTS_DIR>', '--systemname', '<SYSTEMNAME>']}, {'phase': 'run', 'argv': ['open', 'vectordb', 'run', 'file', '--vdb-engine', 'milvus', '--vdb-index', 'HNSW', '--host', '127.0.0.1', '--port', '19530', '--collection', 'ai_vdb_014_hnsw', '--benchmark-mode', 'timed', '--vector-dim', '128', '--num-query-processes', '<QUERY_PROCESSES>', '--runtime', '<DURATION_SEC>', '--loops', '<LOOPS>', '--storage-root', '<STORAGE_ROOT>', '--results-dir', '<RESULTS_DIR>', '--systemname', '<SYSTEMNAME>']}]


def main() -> int:
    parser = argparse.ArgumentParser(description=f"{CASE_ID} direct mlpstorage case")
    parser.add_argument("--mode", choices=("plan", "preflight", "dry-run", "execute"), default="plan")
    parser.add_argument("--data-dir", type=Path, default=Path(os.environ.get("DUT_DATA", "data")))
    parser.add_argument("--results-dir", type=Path, default=Path(os.environ.get("MLPERF_RESULTS_DIR", "results")))
    parser.add_argument("--mlpstorage", type=Path)
    parser.add_argument("--launcher", choices=("single", "mpi"), default="single")
    parser.add_argument("--mpi-bin", choices=("mpiexec", "mpirun"), default="mpiexec" if os.name == "nt" else "mpirun")
    parser.add_argument("--systemname", default=None)
    parser.add_argument("--client-memory-gb", type=int, default=64)
    parser.add_argument("--accelerators", type=int, default=1)
    parser.add_argument("--query-processes", type=int, default=1)
    parser.add_argument("--duration-sec", type=int, default=60)
    parser.add_argument("--loops", type=int, default=1)
    parser.add_argument("--dlio-bin-path", type=Path)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--o-direct", action="store_true")
    parser.add_argument("--confirm-dut", action="store_true")
    parser.add_argument("--init-results", action="store_true")
    parser.add_argument("--cleanup-data", action="store_true")
    parser.add_argument("--cleanup-root", type=Path)
    args = parser.parse_args()

    if NATIVE_STATUS != "SUPPORTED":
        print(f"{CASE_ID} BLOCKED: no native mlpstorage command: {NATIVE_REASON}")
        return 2
    cli = args.mlpstorage
    if cli is None:
        for candidate in (Path(sys.executable).with_name("mlpstorage.exe"), Path(sys.executable).with_name("mlpstorage")):
            if candidate.is_file():
                cli = candidate
                break
    if cli is None:
        cli = Path(shutil.which("mlpstorage") or "mlpstorage")
    selected = [item for item in COMMANDS if args.prepare or item["phase"] != "prepare"]
    values = {
        "<DATA_DIR>": str(args.data_dir.resolve()),
        "<RESULTS_DIR>": str(args.results_dir.resolve()),
        "<CHECKPOINT_DIR>": str(args.data_dir.resolve() / "checkpoint" / CASE_ID),
        "<CACHE_DIR>": str(args.data_dir.resolve() / "kvcache" / CASE_ID),
        "<STORAGE_ROOT>": str(args.data_dir.resolve() / "milvus" / CASE_ID),
        "<SYSTEMNAME>": args.systemname or f"{CASE_ID.lower()}-native",
        "<CLIENT_MEMORY_GB>": str(args.client_memory_gb),
        "<ACCELERATORS>": str(args.accelerators),
        "<QUERY_PROCESSES>": str(args.query_processes),
        "<DURATION_SEC>": str(args.duration_sec),
        "<LOOPS>": str(args.loops),
        "<MPI_BIN>": args.mpi_bin,
    }
    if args.mode == "execute" and not args.confirm_dut:
        print(f"{CASE_ID} BLOCKED: execute requires --confirm-dut")
        return 2
    if args.cleanup_data and args.cleanup_root is None:
        print(f"{CASE_ID} BLOCKED: --cleanup-data requires --cleanup-root")
        return 2

    def finalize(code: int) -> int:
        if not args.cleanup_data:
            return code
        data_path = args.data_dir.resolve()
        root_path = args.cleanup_root.resolve()
        if data_path == root_path or root_path not in data_path.parents:
            print(f"{CASE_ID} CLEANUP_FAILED: data path is outside cleanup root")
            return 1
        try:
            if data_path.exists():
                shutil.rmtree(data_path)
            print(f"TEST_DATA_ROOT={data_path}")
            print(f"TEST_DATA_CLEANED={not data_path.exists()}")
            return code if not data_path.exists() else 1
        except OSError as error:
            print(f"{CASE_ID} CLEANUP_FAILED: {error}")
            return 1

    if args.init_results and args.mode in {"preflight", "dry-run", "execute"}:
        args.results_dir.parent.mkdir(parents=True, exist_ok=True)
        init_command = [str(cli), "init", args.systemname or f"{CASE_ID.lower()}-native", str(args.results_dir.resolve())]
        print(f"{CASE_ID} init: {subprocess.list2cmdline(['mlpstorage', *init_command[1:]])}")
        if args.mode == "execute":
            initialized = subprocess.run(init_command, check=False)
            if initialized.returncode != 0:
                return finalize(initialized.returncode)
    for item in selected:
        command = [str(cli), *[values.get(arg, arg) for arg in item["argv"] if arg != "<COMMAND>"]]
        if args.o_direct and ("training" in command or "checkpointing" in command) and "--o-direct" not in command:
            command.append("--o-direct")
        if args.dlio_bin_path and ("training" in command or "checkpointing" in command):
            command.extend(["--dlio-bin-path", str(args.dlio_bin_path)])
        if args.launcher == "single" and args.mode in {"preflight", "dry-run", "execute"} and "checkpointing" in command and "--num-processes" in command:
            ranks = int(command[command.index("--num-processes") + 1])
            if ranks > 1:
                print(f"{CASE_ID} BLOCKED: checkpointing rank case requires --launcher mpi (requested {ranks} ranks)")
                return finalize(2)
        print(f"{CASE_ID} {item['phase']}: {subprocess.list2cmdline(['mlpstorage', *command[1:]])}")
        if args.mode in {"plan", "preflight"}:
            continue
        if args.mode == "dry-run":
            command.append("--dry-run")
        try:
            completed = subprocess.run(command, check=False)
        except OSError as error:
            print(f"{CASE_ID} FAIL phase={item['phase']}: {error}")
            return finalize(1)
        if completed.returncode != 0:
            print(f"{CASE_ID} FAIL phase={item['phase']} rc={completed.returncode}")
            return finalize(completed.returncode)
    if args.mode == "preflight" and not cli.is_file() and shutil.which(str(cli)) is None:
        print(f"{CASE_ID} BLOCKED: mlpstorage executable not found: {cli}")
        return 2
    if args.mode == "dry-run":
        print(f"{CASE_ID} DRY_RUN (not a workload PASS)")
        return 3
    if args.mode == "execute":
        print(f"{CASE_ID} PASS")
    return finalize(0)


if __name__ == "__main__":
    raise SystemExit(main())
