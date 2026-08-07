"""Safe command builder and executor for FULL_TEST_PLAN case entrypoints.

The workbook's original command is always preserved in the manifest.  The
adapter below emits commands for the CLI exposed by this checkout.  A case is
reported as BLOCKED when the installed CLI cannot represent its workload;
the runner never substitutes a generic I/O probe and calls that a formal run.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence

from full_test_plan_cases.catalog import SOURCE_SHA256, get_case


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class RunOptions:
    data_dir: Path
    results_dir: Path
    launcher: str = "single"
    mpi_bin: str = "mpiexec"
    mlpstorage: Path | str | None = None
    dry_run: bool = True
    engineering_smoke: bool = False
    matrix: bool = False
    repeats: int = 1
    prepare: bool = False
    accelerators: int = 1
    client_memory_gb: int = 64
    duration_sec: int = 60
    query_processes: int = 1
    num_vectors: int | None = None
    vector_dimension: int | None = None
    users: int | None = None
    o_direct: bool = False
    custom_command: str | None = None


def _find_mlpstorage(value: Path | str | None) -> str:
    if value is not None:
        return str(value)
    candidates = (
        REPO_ROOT / ".venv" / "Scripts" / "mlpstorage.exe",
        REPO_ROOT / ".venv" / "Scripts" / "mlpstorage",
        REPO_ROOT / ".venv" / "bin" / "mlpstorage",
    )
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return shutil.which("mlpstorage") or "mlpstorage"


def _find_dlio(mlpstorage: str) -> str:
    cli_path = Path(mlpstorage)
    sibling_names = ("dlio_benchmark.exe", "dlio_benchmark") if os.name == "nt" else ("dlio_benchmark",)
    for name in sibling_names:
        sibling = cli_path.with_name(name)
        if sibling.is_file():
            return str(sibling.parent)
    found = shutil.which("dlio_benchmark")
    return str(Path(found).parent) if found else str(cli_path.parent)


def _launcher_args(options: RunOptions) -> tuple[list[str], str]:
    if options.launcher == "single":
        return ["--exec-type", "docker"], "single process; no Docker engine is used"
    if options.launcher == "mpi":
        return ["--exec-type", "mpi", "--mpi-bin", options.mpi_bin], "MPI multi-process launch"
    raise ValueError(f"Unsupported launcher: {options.launcher}")


def _nonformal_args(options: RunOptions) -> list[str]:
    args = ["--dry-run"] if options.dry_run else []
    if options.dry_run or options.engineering_smoke:
        args.extend(["--allow-invalid-params", "--skip-validation", "--skip-fs-separation-gate"])
    return args


def _training_params(options: RunOptions, *extra: str) -> list[str]:
    values: list[str] = []
    if options.dry_run or options.engineering_smoke:
        values.append("dataset.num_files_train=8")
    if os.name == "nt":
        values.append("reader.multiprocessing_context=spawn")
    values.extend(extra)
    return ["--params", *values] if values else []


def _timeseries_args(options: RunOptions) -> list[str]:
    return ["--skip-timeseries"] if options.dry_run or options.engineering_smoke else []


def _blocked(case: dict[str, Any], options: RunOptions, reason: str) -> dict[str, Any]:
    _, explanation = _launcher_args(options)
    return {
        "case_id": case["case_id"],
        "status": "BLOCKED",
        "reason": reason,
        "commands": [],
        "launcher": options.launcher,
        "launcher_explanation": explanation,
        "source_command": case["source_command"],
    }


def _custom_plan(case: dict[str, Any], options: RunOptions) -> dict[str, Any]:
    if os.name == "nt":
        command = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", options.custom_command or ""]
    else:
        command = ["bash", "-lc", options.custom_command or ""]
    _, explanation = _launcher_args(options)
    plan = {
        "case_id": case["case_id"],
        "status": "READY",
        "reason": "approved custom workload command" if not options.dry_run else "custom command preview only",
        "commands": [] if options.dry_run else [command],
        "launcher": options.launcher,
        "launcher_explanation": explanation,
        "source_command": case["source_command"],
    }
    if options.dry_run:
        plan["preview_command"] = command
    return plan


def _slash_values(text: str, label: str) -> list[int]:
    match = re.search(rf"\b{re.escape(label)}\s+([0-9]+(?:/[0-9]+)+)", text, re.I)
    return [int(value) for value in match.group(1).split("/")] if match else []


def _training_plan(case: dict[str, Any], options: RunOptions) -> dict[str, Any]:
    cli = _find_mlpstorage(options.mlpstorage)
    dlio = _find_dlio(cli)
    config = case["model_config"]
    lowered = config.lower()
    if case["case_id"] in {"AI-TRN-014", "AI-TRN-015", "AI-TRN-016"}:
        model, accelerator = "unet3d", "b200"
        assumption = "generic matrix case anchored to current UNet3D/B200 workload"
    else:
        model_match = re.search(r"(unet3d|retinanet|cosmoflow|resnet50|dlrm|flux)", lowered)
        accelerator_match = re.search(r"(a100|h100|b200|mi355)", lowered)
        model = model_match.group(1) if model_match else ""
        accelerator = accelerator_match.group(1) if accelerator_match else ""
        assumption = None
    if model not in {"unet3d", "retinanet"}:
        return _blocked(case, options, f"current mlpstorage training CLI does not expose model {model or config}")
    if accelerator not in {"b200", "mi355"}:
        return _blocked(case, options, f"current mlpstorage training CLI does not expose accelerator {accelerator or config}")

    launcher, explanation = _launcher_args(options)
    workload_results = options.results_dir / case["case_id"] / "workload"
    common = [
        "--data-dir", str(options.data_dir),
        "--results-dir", str(workload_results),
        "--systemname", f"full-{case['case_id'].lower()}",
        "--dlio-bin-path", dlio,
        *launcher,
    ]
    commands: list[list[str]] = []
    if options.prepare or options.dry_run:
        commands.append([
            cli, "open", "training", model, "datagen", "file",
            "--num-processes", "1",
            *common,
            *_training_params(options),
            *_nonformal_args(options),
        ])
    accelerator_values = [options.accelerators]
    if options.matrix:
        accelerator_values = _slash_values(case["primary_variables"], "accelerators") or accelerator_values
    thread_values: list[int | None] = [None]
    if options.matrix and case["case_id"] == "AI-TRN-015":
        thread_values = _slash_values(case["primary_variables"], "threads") or thread_values
    for accelerator_count in accelerator_values:
        for read_threads in thread_values:
            run_command = [
                cli, "open", "training", model, "run", "file",
                "--accelerator-type", accelerator,
                "--client-host-memory-in-gb", str(options.client_memory_gb),
                "--num-accelerators", str(accelerator_count),
                "--loops", str(options.repeats),
                *common,
                *_training_params(options, *([f"reader.read_threads={read_threads}"] if read_threads is not None else [])),
            ]
            run_command.extend([*_timeseries_args(options), *_nonformal_args(options)])
            if options.o_direct:
                run_command.append("--o-direct")
            commands.append(run_command)
    plan = {
        "case_id": case["case_id"],
        "status": "READY",
        "reason": "mapped to current mlpstorage training CLI",
        "commands": commands,
        "launcher": options.launcher,
        "launcher_explanation": explanation,
        "source_command": case["source_command"],
    }
    if assumption:
        plan["adapter_assumption"] = assumption
    return plan


def _checkpoint_plan(case: dict[str, Any], options: RunOptions) -> dict[str, Any]:
    if case["case_id"] == "AI-CKP-008":
        return _blocked(
            case,
            options,
            "cold/warm restore requires an operator-approved purge/reboot step between write-only and read-only phases",
        )
    cli = _find_mlpstorage(options.mlpstorage)
    dlio = _find_dlio(cli)
    config = case["model_config"].lower()
    model_match = re.search(r"(?:llama3-)?(8b|70b|405b|1t)", config)
    model = f"llama3-{model_match.group(1)}" if model_match else "llama3-8b"
    rank_match = re.search(r"(\d+)[- ]rank", config)
    ranks = int(rank_match.group(1)) if rank_match else 8
    launcher, explanation = _launcher_args(options)
    workload_results = options.results_dir / case["case_id"] / "workload"
    counts = [1]
    if case["case_id"] in {"AI-CKP-001", "AI-CKP-007", "AI-CKP-009"}:
        counts = [10]
    if case["case_id"] == "AI-CKP-009" and options.matrix:
        counts = [1, 2, 10]
    commands = []
    for count in counts:
        commands.append([
            cli, "open", "checkpointing", "run", "file",
            "--model", model,
            "--num-processes", str(ranks),
            "--client-host-memory-in-gb", str(options.client_memory_gb),
            "--checkpoint-folder", str(options.data_dir / "checkpoint" / case["case_id"]),
            "--num-checkpoints-read", str(count),
            "--num-checkpoints-write", str(count),
            "--results-dir", str(workload_results),
            "--systemname", f"full-{case['case_id'].lower()}",
            "--dlio-bin-path", dlio,
            *launcher,
            *_nonformal_args(options),
        ])
    return {
        "case_id": case["case_id"],
        "status": "READY",
        "reason": "mapped to current mlpstorage checkpointing CLI",
        "commands": commands,
        "launcher": options.launcher,
        "launcher_explanation": explanation,
        "source_command": case["source_command"],
        "adapter_assumption": "generic checkpoint matrix cases use llama3-8b unless the case names a model",
    }


def _kv_model(config: str) -> str | None:
    lowered = config.lower()
    for token, model in (
        ("llama3.1-70b", "llama3.1-70b-instruct"),
        ("llama3.1-8b", "llama3.1-8b"),
        ("mistral-7b", "mistral-7b"),
        ("llama2-7b", "llama2-7b"),
        ("tiny-1b", "tiny-1b"),
    ):
        if token in lowered:
            return model
    if any(token in lowered for token in ("deepseek", "qwen", "gpt-oss", "burstgpt", "sharegpt")):
        return None
    return "llama3.1-8b"


def _kv_plan(case: dict[str, Any], options: RunOptions) -> dict[str, Any]:
    if case["case_id"] in {"AI-KV-021", "AI-KV-022"}:
        return _blocked(case, options, "trace replay requires the case trace file and its replay adapter")
    model = _kv_model(case["model_config"])
    if not model:
        return _blocked(case, options, f"current mlpstorage KV Cache CLI does not expose {case['model_config']}")
    cli = _find_mlpstorage(options.mlpstorage)
    defaults = {
        "AI-KV-001": {"users": 200, "gpu": 0, "cpu": 0, "alloc": 16},
        "AI-KV-002": {"users": 100, "gpu": 0, "cpu": 4, "alloc": 16},
        "AI-KV-003": {"users": 70, "gpu": 0, "cpu": 0, "alloc": 4},
    }.get(case["case_id"], {})
    users_match = re.search(r"(\d+) users", case["primary_variables"], re.I)
    default_users = int(defaults.get("users", int(users_match.group(1)) if users_match else 10))
    user_values = [options.users or default_users]
    if options.matrix and options.users is None:
        user_values = _slash_values(case["primary_variables"], "users") or user_values
        range_match = re.search(r"users\s+(\d+)\s+to\s+(\d+)", case["primary_variables"], re.I)
        if range_match:
            user_values = [int(range_match.group(1)), int(range_match.group(2))]
    generation_modes = ["none"]
    if options.matrix and case["case_id"] == "AI-KV-018":
        generation_modes = ["none", "fast", "realistic"]
    capacity_values: list[int | None] = [None]
    if options.matrix and case["case_id"] == "AI-KV-013":
        capacity_values = [0, 4, 16, 32]
    allocation_values: list[int | None] = [int(defaults["alloc"])] if "alloc" in defaults else [None]
    if options.matrix and case["case_id"] == "AI-KV-006":
        allocation_values = [1, 2, 4, 8]
    launcher, explanation = _launcher_args(options)
    workload_results = options.results_dir / case["case_id"] / "workload"
    commands = []
    for users in user_values:
        for generation_mode in generation_modes:
            for capacity in capacity_values:
                for allocation in allocation_values:
                    command = [
                        cli, "open", "kvcache", "run",
                        "--model", model,
                        "--num-users", str(users),
                        "--duration", str(options.duration_sec),
                        "--generation-mode", generation_mode,
                        "--trials", "1" if options.dry_run or options.engineering_smoke else "3",
                        "--inter-option-delay", "0" if options.dry_run or options.engineering_smoke else "20",
                        "--loops", str(options.repeats),
                        "--num-processes", "1",
                        "--hosts", "localhost",
                        "--cache-dir", str(options.data_dir / "kvcache" / case["case_id"]),
                        "--results-dir", str(workload_results),
                        "--systemname", f"full-{case['case_id'].lower()}",
                        *launcher,
                    ]
                    gpu_value = capacity if capacity is not None else defaults.get("gpu")
                    cpu_value = capacity if capacity is not None else defaults.get("cpu")
                    if gpu_value is not None:
                        command.extend(["--gpu-mem-gb", str(gpu_value)])
                    if cpu_value is not None:
                        command.extend(["--cpu-mem-gb", str(cpu_value)])
                    if allocation is not None:
                        command.extend(["--max-concurrent-allocs", str(allocation)])
                    command.extend([*_timeseries_args(options), *_nonformal_args(options)])
                    commands.append(command)
    return {
        "case_id": case["case_id"],
        "status": "READY",
        "reason": "mapped to current mlpstorage KV Cache CLI",
        "commands": commands,
        "launcher": options.launcher,
        "launcher_explanation": explanation,
        "source_command": case["source_command"],
    }


def _vdb_index(config: str) -> str:
    normalized = config.upper().replace("-", "_")
    for index in ("DISKANN", "HNSW", "AISAQ", "IVF_SQ8", "IVF_FLAT", "FLAT"):
        if index in normalized:
            return index
    return "HNSW"


def _vdb_plan(case: dict[str, Any], options: RunOptions) -> dict[str, Any]:
    if case["case_id"] == "AI-VDB-015":
        return _blocked(case, options, "logical trace replay requires --custom-command with the selected trace path")
    cli = _find_mlpstorage(options.mlpstorage)
    config = case["model_config"]
    index = _vdb_index(config)
    indices = [index]
    if options.matrix and case["case_id"] == "AI-VDB-008":
        indices = ["DISKANN", "HNSW", "AISAQ", "IVF_FLAT", "IVF_SQ8", "FLAT"]
    dim_match = re.search(r"[x×](\d+)", config, re.I)
    dimension = options.vector_dimension or (int(dim_match.group(1)) if dim_match else 128)
    declared_vectors = 10_000_000 if re.search(r"\b10M", config, re.I) else (1_000_000 if re.search(r"\b1M", config, re.I) else 1_000)
    num_vectors = options.num_vectors or (1_000 if options.dry_run or options.engineering_smoke else declared_vectors)
    query_processes = [options.query_processes]
    if options.matrix:
        query_processes = {
            "AI-VDB-006": [1, 4, 8],
            "AI-VDB-010": [1, 2, 4, 8, 16],
        }.get(case["case_id"], query_processes)
    search_efs: list[int | None] = [None]
    if options.matrix:
        search_efs = {
            "AI-VDB-002": [32, 128, 256],
            "AI-VDB-007": [32, 64, 128, 256, 512],
            "AI-VDB-009": [32, 64, 128, 256, 512],
        }.get(case["case_id"], search_efs)
    batch_sizes: list[int | None] = [None]
    if options.matrix and case["case_id"] == "AI-VDB-011":
        batch_sizes = [1, 8, 32, 64]
    search_limits: list[int | None] = [None]
    if options.matrix and case["case_id"] == "AI-VDB-013":
        search_limits = [10, 100]
    workload_results = options.results_dir / case["case_id"] / "workload"
    commands: list[list[str]] = []
    for current_index in indices:
        collection = f"{case['case_id'].lower().replace('-', '_')}_{current_index.lower()}"
        if options.prepare or options.dry_run:
            commands.append([
                cli, "open", "vectordb", "datagen", "file",
                "--vdb-engine", "milvus",
                "--vdb-index", current_index,
                "--host", "127.0.0.1",
                "--port", "19530",
                "--collection", collection,
                "--num-vectors", str(num_vectors),
                "--dimension", str(dimension),
                "--num-shards", "1",
                "--force",
                "--results-dir", str(workload_results),
                "--systemname", f"full-{case['case_id'].lower()}",
                *_nonformal_args(options),
            ])
        for query_count in query_processes:
            for search_ef in search_efs:
                for batch_size in batch_sizes:
                    for search_limit in search_limits:
                        command = [
                            cli, "open", "vectordb", "run", "file",
                            "--vdb-engine", "milvus",
                            "--vdb-index", current_index,
                            "--host", "127.0.0.1",
                            "--port", "19530",
                            "--collection", collection,
                            "--vector-dim", str(dimension),
                            "--num-query-processes", str(query_count),
                            "--runtime", str(options.duration_sec),
                            "--loops", str(options.repeats),
                            "--storage-root", str(options.data_dir / "milvus"),
                            "--results-dir", str(workload_results),
                            "--systemname", f"full-{case['case_id'].lower()}",
                        ]
                        if search_ef is not None:
                            command.extend(["--search-ef", str(search_ef)])
                        if batch_size is not None:
                            command.extend(["--batch-size", str(batch_size)])
                        if search_limit is not None:
                            command.extend(["--search-limit", str(search_limit), "--recall-k", str(search_limit)])
                        command.extend([*_timeseries_args(options), *_nonformal_args(options)])
                        commands.append(command)
    return {
        "case_id": case["case_id"],
        "status": "READY",
        "reason": "mapped to current mlpstorage VectorDB CLI; Milvus must already be healthy",
        "commands": commands,
        "launcher": "local",
        "launcher_explanation": "single local VectorDB client; no Docker engine is started by this script",
        "source_command": case["source_command"],
    }


def build_workload_plan(case: dict[str, Any], options: RunOptions) -> dict[str, Any]:
    """Build commands for the installed CLI without executing them."""
    if options.custom_command:
        return _custom_plan(case, options)
    family = case["family"]
    if family == "Training":
        return _training_plan(case, options)
    if family == "Checkpoint":
        return _checkpoint_plan(case, options)
    if family == "KV Cache":
        return _kv_plan(case, options)
    if family == "VectorDB":
        return _vdb_plan(case, options)
    if family == "Base":
        if case["case_id"] == "AI-BASE-001":
            command = [
                "powershell.exe", "-NoProfile", "-Command",
                "Get-Disk | Format-Table Number,FriendlyName,SerialNumber,OperationalStatus,HealthStatus,Size; "
                "Get-PhysicalDisk | Format-Table FriendlyName,SerialNumber,HealthStatus,OperationalStatus,Size",
            ]
            _, explanation = _launcher_args(options)
            plan = {
                "case_id": case["case_id"], "status": "READY", "reason": "read-only Windows inventory",
                "commands": [] if options.dry_run else [command], "launcher": "local", "launcher_explanation": explanation,
                "source_command": case["source_command"],
            }
            if options.dry_run:
                plan["preview_command"] = command
            return plan
        return _blocked(case, options, "base case requires its authorized DUT PowerShell workload via --custom-command")
    return _blocked(case, options, "mixed case requires explicit component commands and orchestration via --custom-command")


def _parser(case: dict[str, Any]) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"{case['case_id']} · {case['purpose']}")
    parser.add_argument("--mode", choices=("plan", "preflight", "dry-run", "execute"), default="plan")
    parser.add_argument("--data-dir", type=Path, default=Path(os.environ.get("DUT_DATA", "data")))
    parser.add_argument("--results-dir", type=Path, default=Path(os.environ.get("AI_SSD_RESULTS", "results/full_test_plan")))
    parser.add_argument("--launcher", choices=("single", "mpi"), default="single")
    parser.add_argument("--mpi-bin", choices=("mpiexec", "mpirun"), default="mpiexec" if os.name == "nt" else "mpirun")
    parser.add_argument("--mlpstorage", type=Path)
    parser.add_argument("--engineering-smoke", action="store_true", help="use a deliberately reduced, non-submittable workload")
    parser.add_argument("--matrix", action="store_true", help="expand every supported sweep point declared by this Case")
    parser.add_argument("--repeats", type=int, help="workload loops per sweep point; formal default is 3")
    parser.add_argument("--prepare", action="store_true", help="run the case's data-generation step before the workload")
    parser.add_argument("--accelerators", type=int, default=1)
    parser.add_argument("--client-memory-gb", type=int, default=64)
    parser.add_argument("--duration-sec", type=int, default=60)
    parser.add_argument("--query-processes", type=int, default=1)
    parser.add_argument("--num-vectors", type=int)
    parser.add_argument("--vector-dimension", type=int)
    parser.add_argument("--users", type=int)
    parser.add_argument("--o-direct", action="store_true")
    parser.add_argument("--custom-command", help="approved exact workload command for unsupported or composite cases")
    parser.add_argument("--confirm-dut", action="store_true", help="required for mode=execute")
    return parser


def _options(args: argparse.Namespace) -> RunOptions:
    return RunOptions(
        data_dir=args.data_dir.resolve(),
        results_dir=args.results_dir.resolve(),
        launcher=args.launcher,
        mpi_bin=args.mpi_bin,
        mlpstorage=args.mlpstorage,
        dry_run=args.mode in {"plan", "preflight", "dry-run"},
        engineering_smoke=args.engineering_smoke,
        matrix=args.matrix,
        repeats=args.repeats or (1 if args.mode in {"plan", "preflight", "dry-run"} or args.engineering_smoke else 3),
        prepare=args.prepare,
        accelerators=args.accelerators,
        client_memory_gb=args.client_memory_gb,
        duration_sec=args.duration_sec,
        query_processes=args.query_processes,
        num_vectors=args.num_vectors,
        vector_dimension=args.vector_dimension,
        users=args.users,
        o_direct=args.o_direct,
        custom_command=args.custom_command,
    )


def _preflight(plan: dict[str, Any], options: RunOptions) -> dict[str, Any]:
    checks: dict[str, Any] = {
        "plan_ready": plan["status"] == "READY",
        "data_results_distinct": options.data_dir != options.results_dir,
    }
    if plan["commands"]:
        executable = plan["commands"][0][0]
        checks["first_executable"] = executable
        checks["first_executable_found"] = Path(executable).is_file() or shutil.which(executable) is not None
    checks["ready"] = all(value for key, value in checks.items() if key.endswith("_ready") or key.endswith("_distinct") or key.endswith("_found"))
    return checks


def _command_workdir(command: Sequence[str], case_dir: Path) -> Path:
    # mlpstorage captures the current directory as its code image.  Running
    # outside the checkout avoids unrelated editor lock files (for example
    # docs/~$*.xlsx) making an otherwise valid Windows run fail.
    return case_dir if "mlpstorage" in Path(command[0]).name.lower() else REPO_ROOT


def _initialize_results_if_needed(command: Sequence[str], cwd: Path) -> dict[str, Any] | None:
    if "mlpstorage" not in Path(command[0]).name.lower():
        return None
    if "--results-dir" not in command:
        return None
    result_dir = Path(command[command.index("--results-dir") + 1])
    if (result_dir / "mlperf-results.yaml").is_file():
        return None
    result_dir.mkdir(parents=True, exist_ok=True)
    init = subprocess.run(
        [command[0], "init", "full-test-plan", str(result_dir)],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return {"returncode": init.returncode, "stdout": init.stdout[-2000:], "stderr": init.stderr[-2000:]}


def classify_command_status(returncode: int, output: str) -> str:
    """Classify process completion without treating command generation as a workload pass."""
    if "dry-run mode" in output.lower():
        return "DRY_RUN"
    return "PASS" if returncode == 0 else "FAIL"


def _execute_commands(commands: list[list[str]], case_dir: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for index, command in enumerate(commands, start=1):
        cwd = _command_workdir(command, case_dir)
        init = _initialize_results_if_needed(command, cwd)
        command_env = os.environ.copy()
        if "mlpstorage" in Path(command[0]).name.lower():
            # An explicitly selected venv console script does not automatically
            # add its Scripts directory to PATH on Windows.  DLIO dependency
            # discovery uses PATH before the configured directory, so expose
            # the already-installed sibling executables to the child process.
            command_env["PATH"] = f"{Path(command[0]).parent}{os.pathsep}{command_env.get('PATH', '')}"
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=command_env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        stdout_path = case_dir / f"command_{index:02d}.stdout.log"
        stderr_path = case_dir / f"command_{index:02d}.stderr.log"
        stdout_path.write_text(completed.stdout, encoding="utf-8")
        stderr_path.write_text(completed.stderr, encoding="utf-8")
        combined_output = f"{completed.stdout}\n{completed.stderr}"
        status = classify_command_status(completed.returncode, combined_output)
        results.append({
            "command": command,
            "command_text": subprocess.list2cmdline(command) if os.name == "nt" else shlex.join(command),
            "returncode": completed.returncode,
            "status": status,
            "dry_run_detected": status == "DRY_RUN",
            "stdout": str(stdout_path),
            "stderr": str(stderr_path),
            "init": init,
        })
    return results


def run_case(case_id: str, argv: Sequence[str] | None = None) -> int:
    case = get_case(case_id)
    args = _parser(case).parse_args(list(argv) if argv is not None else None)
    options = _options(args)
    plan = build_workload_plan(case, options)
    case_dir = options.results_dir / case["case_id"]
    case_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "source_sha256": SOURCE_SHA256,
        "mode": args.mode,
        "case": case,
        "options": {key: str(value) if isinstance(value, Path) else value for key, value in asdict(options).items()},
        "workload_plan": plan,
    }
    manifest_path = case_dir / "manifest.json"
    if args.mode in {"preflight", "dry-run", "execute"}:
        manifest["preflight"] = _preflight(plan, options)
    if args.mode == "execute" and not args.confirm_dut:
        manifest["status"] = "BLOCKED"
        manifest["reason"] = "mode=execute requires --confirm-dut"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{case['case_id']} BLOCKED: add --confirm-dut after checking paths and capacity")
        return 2
    if args.mode in {"dry-run", "execute"}:
        if plan["status"] != "READY":
            manifest["status"] = "BLOCKED"
            manifest["reason"] = plan["reason"]
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"{case['case_id']} BLOCKED: {plan['reason']}")
            return 2
        command_results = _execute_commands(plan["commands"], case_dir)
        manifest["command_results"] = command_results
        if args.mode == "dry-run" and not any(item["status"] == "FAIL" for item in command_results):
            manifest["status"] = "DRY_RUN"
        elif all(item["status"] == "PASS" for item in command_results):
            manifest["status"] = "SMOKE_PASS" if options.engineering_smoke and args.mode == "execute" else "PASS"
        else:
            manifest["status"] = "FAIL"
    else:
        manifest["status"] = "PLANNED" if args.mode == "plan" else ("READY" if manifest["preflight"]["ready"] else "BLOCKED")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{case['case_id']} {manifest['status']} -> {manifest_path}")
    return 0 if manifest["status"] in {"PLANNED", "READY", "DRY_RUN", "PASS", "SMOKE_PASS"} else 2


def main(case_id: str | None = None) -> int:
    if case_id is not None:
        return run_case(case_id)
    parser = argparse.ArgumentParser(description="Run one FULL_TEST_PLAN case")
    parser.add_argument("case_id")
    args, remaining = parser.parse_known_args()
    return run_case(args.case_id, remaining)


if __name__ == "__main__":
    raise SystemExit(main())
