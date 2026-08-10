"""Common executable runner for the consumer AI-PC SSD test cases.

The runner deliberately fails closed.  A case that needs a missing trace,
Milvus, a subset fixture, or destructive permission produces ``NOT_RUN`` with
an explicit reason instead of silently substituting a different workload.
Every invocation writes ``manifest.json``, command logs and ``verdict.json``
under the selected results root.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

from .catalog import CASES, CaseSpec, get_case


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESULTS_ROOT = REPO_ROOT / "outputs" / "ai_ssd_case_runs"
PS1 = REPO_ROOT / "tools" / "record_windows_io.ps1"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _json_dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _powershell() -> str | None:
    for name in ("pwsh", "powershell"):
        path = shutil.which(name)
        if path:
            return path
    return None


def _tool_exists(name: str) -> bool:
    return shutil.which(name) is not None


def _path_text(path: Path) -> str:
    return str(path.expanduser().resolve())


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _parser(case: CaseSpec) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=f"Execute {case.case_id}: {case.purpose}",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--dut-root", type=Path, default=None, help="DUT data/cache/checkpoint root")
    parser.add_argument(
        "--results-root",
        type=Path,
        default=Path(os.environ.get("AI_SSD_RESULTS_ROOT", DEFAULT_RESULTS_ROOT)),
        help="Evidence output root; keep it off the DUT when possible",
    )
    parser.add_argument("--data-dir", type=Path, default=None, help="Training data or auxiliary input directory")
    parser.add_argument("--cache-dir", type=Path, default=None, help="KV cache directory")
    parser.add_argument("--checkpoint-dir", type=Path, default=None, help="Checkpoint directory")
    parser.add_argument("--mode", choices=("execute", "dry-run", "preflight"), default="execute")
    parser.add_argument("--monitor", action="store_true", help="Wrap the command with Windows ETW/PhysicalDisk capture")
    parser.add_argument("--confirm-destructive", action="store_true", help="Allow overwrite or long-soak actions")
    parser.add_argument("--allow-full-model", action="store_true", help="Allow a full large-model command where no subset fixture exists")
    parser.add_argument("--accelerator-type", choices=("a100", "h100", "b200", "mi355"), default=None)
    parser.add_argument("--num-accelerators", type=int, default=1)
    parser.add_argument("--num-processes", type=int, default=8)
    parser.add_argument("--host-memory-gb", type=int, default=64)
    parser.add_argument("--users", type=int, default=25)
    parser.add_argument("--duration", type=int, default=None, help="Override the case runtime in seconds")
    parser.add_argument("--repeat", type=int, default=1, help="Repeat count for checkpoint profile actions")
    parser.add_argument("--direct", action="store_true", help="Use direct/unbuffered mode where supported")
    parser.add_argument("--extra-arg", action="append", default=[], help="Append one argument to the underlying command")
    return parser


def _resolve_paths(args: argparse.Namespace, case: CaseSpec) -> dict[str, Path]:
    dut = args.dut_root or (Path(os.environ["AI_SSD_DUT_ROOT"]) if os.environ.get("AI_SSD_DUT_ROOT") else None)
    if dut is None:
        dut = REPO_ROOT / "outputs" / "ai_ssd_case_dut_placeholder"
    results_root = args.results_root
    data = args.data_dir or dut / "data"
    cache = args.cache_dir or dut / "kv_cache"
    checkpoint = args.checkpoint_dir or dut / "checkpoints"
    return {
        "dut": dut,
        "results_root": results_root,
        "data": data,
        "cache": cache,
        "checkpoint": checkpoint,
    }


def _base_mlp(division: str, benchmark: str, action: str, storage: str | None = None) -> list[str]:
    command = [sys.executable, "-m", "mlpstorage_py.main", division, benchmark, action]
    if storage:
        command.append(storage)
    return command


def _common_mlp_args(paths: dict[str, Path], results_dir: Path, case: CaseSpec) -> list[str]:
    return [
        "--results-dir", _path_text(results_dir),
        "--systemname", case.case_id,
        "--mpi-bin", "mpiexec",
        "--skip-validation",
        "--skip-fs-separation-gate",
        "--verbose",
    ]


def _training_command(
    args: argparse.Namespace,
    paths: dict[str, Path],
    result_dir: Path,
    case: CaseSpec,
    *,
    run: bool = True,
    model_override: str | None = None,
) -> list[str]:
    model = model_override or case.default_model or "unet3d"
    division = "open"
    accelerator = args.accelerator_type or "b200"
    action = "run" if run else "datagen"
    if run:
        command = _base_mlp(division, "training", action, "file") + [
            "--accelerator-type", accelerator,
            "--client-host-memory-in-gb", str(args.host_memory_gb),
            "--num-accelerators", str(args.num_accelerators),
            "--data-dir", _path_text(paths["data"]),
        ]
    else:
        command = _base_mlp(division, "training", action, "file") + [
            "--num-processes", str(max(1, args.num_processes)),
            "--data-dir", _path_text(paths["data"]),
        ]
    command.extend(_common_mlp_args(paths, result_dir, case))
    if args.direct:
        command.append("--o-direct")
    command.extend(args.extra_arg)
    return command


def _checkpoint_command(
    args: argparse.Namespace,
    paths: dict[str, Path],
    result_dir: Path,
    case: CaseSpec,
    *,
    writes: int = 1,
    reads: int = 1,
) -> list[str]:
    model = case.default_model or "llama3-8b"
    division = "open"
    command = _base_mlp(division, "checkpointing", "run", "file") + [
        "--model", model,
        "--num-processes", str(args.num_processes),
        "--client-host-memory-in-gb", str(args.host_memory_gb),
        "--checkpoint-folder", _path_text(paths["checkpoint"]),
        "--num-checkpoints-write", str(writes),
        "--num-checkpoints-read", str(reads),
    ]
    command.extend(_common_mlp_args(paths, result_dir, case))
    if args.direct:
        command.append("--o-direct")
    command.extend(args.extra_arg)
    return command


def _kv_command(
    args: argparse.Namespace,
    paths: dict[str, Path],
    result_dir: Path,
    case: CaseSpec,
    *,
    cpu_gb: int = 0,
    model_override: str | None = None,
) -> list[str]:
    model = model_override or case.default_model or "llama3.1-8b"
    duration = args.duration or 60
    command = _base_mlp("open", "kvcache", "run") + [
        "--model", model,
        "--num-users", str(args.users),
        "--duration", str(duration),
        "--gpu-mem-gb", "0",
        "--cpu-mem-gb", str(cpu_gb),
        "--cache-dir", _path_text(paths["cache"]),
        "--results-dir", _path_text(result_dir),
        "--systemname", case.case_id,
        "--skip-validation",
        "--skip-fs-separation-gate",
        "--skip-ssh-check",
        "--verbose",
    ]
    if args.direct:
        command.extend(["--performance-profile", "throughput"])
    command.extend(args.extra_arg)
    return command


def _vdb_command(args: argparse.Namespace, paths: dict[str, Path], result_dir: Path, case: CaseSpec, *, index: str = "HNSW", dim: int = 128) -> list[str]:
    duration = args.duration or 30
    command = _base_mlp("open", "vectordb", "run", "object") + [
        "--vdb-engine", "milvus",
        "--vdb-index", index,
        "--vector-dim", str(dim),
        "--storage-type", "file",
        "--storage-root", _path_text(paths["dut"]),
        "--runtime", str(duration),
        "--num-query-processes", str(max(1, args.num_processes)),
        "--num-query-vectors", "100",
        "--search-limit", "10",
        "--results-dir", _path_text(result_dir),
        "--systemname", case.case_id,
        "--skip-validation",
        "--skip-fs-separation-gate",
        "--skip-ssh-check",
        "--verbose",
    ]
    command.extend(args.extra_arg)
    return command


def _build_commands(args: argparse.Namespace, paths: dict[str, Path], result_dir: Path, case: CaseSpec) -> list[list[str]]:
    kind = case.kind
    if kind == "training_smoke":
        return [_training_command(args, paths, result_dir, case, run=False), _training_command(args, paths, result_dir, case, run=True)]
    if kind in {"training_profile"}:
        return [_training_command(args, paths, result_dir, case, run=True)]
    if kind == "checkpoint_smoke":
        return [_checkpoint_command(args, paths, result_dir, case, writes=1, reads=1)]
    if kind == "checkpoint_profile":
        count = max(1, min(args.repeat, 10))
        return [_checkpoint_command(args, paths, result_dir, case, writes=count, reads=count)]
    if kind == "checkpoint_burst":
        count = max(1, min(args.repeat, 10))
        return [_checkpoint_command(args, paths, result_dir, case, writes=count, reads=0)]
    if kind == "checkpoint_subset":
        if not args.allow_full_model:
            raise RuntimeError("No subset flag exists in the current CLI; explicitly pass --allow-full-model")
        return [_checkpoint_command(args, paths, result_dir, case, writes=1, reads=1)]
    if kind in {"kv_smoke", "kv_native", "kv_persona"}:
        return [_kv_command(args, paths, result_dir, case, cpu_gb=4 if kind == "kv_persona" else 0)]
    if kind == "kv_spill":
        return [_kv_command(args, paths, result_dir, case, cpu_gb=4)]
    if kind == "vdb_smoke":
        return [_vdb_command(args, paths, result_dir, case, index="HNSW", dim=128)]
    if kind == "vdb_native":
        return [_vdb_command(args, paths, result_dir, case, index="HNSW", dim=1536)]
    if kind == "vdb_large":
        return [_vdb_command(args, paths, result_dir, case, index="DISKANN", dim=1536)]
    if kind == "vdb_aisaq":
        return [_vdb_command(args, paths, result_dir, case, index="AISAQ", dim=512)]
    if kind == "mix_kv_checkpoint":
        return [
            _kv_command(args, paths, result_dir, case, cpu_gb=0, model_override="llama3.1-8b"),
            _checkpoint_command(args, paths, result_dir, case, writes=1, reads=0),
        ]
    if kind == "mix_vdb":
        return [_vdb_command(args, paths, result_dir, case, index="HNSW", dim=1536)]
    if kind == "mix_training_checkpoint":
        return [
            _training_command(args, paths, result_dir, case, run=True, model_override="unet3d"),
            _checkpoint_command(args, paths, result_dir, case, writes=1, reads=0),
        ]
    if kind == "soak_mixed":
        return [
            _kv_command(args, paths, result_dir, case, cpu_gb=0, model_override="llama3.1-8b"),
            _checkpoint_command(args, paths, result_dir, case, writes=1, reads=0),
            _vdb_command(args, paths, result_dir, case, index="HNSW", dim=128),
        ]
    raise RuntimeError(f"No command builder for {case.case_id} ({kind})")


def _preflight(case: CaseSpec, args: argparse.Namespace, paths: dict[str, Path]) -> list[str]:
    issues: list[str] = []
    if os.name != "nt":
        issues.append("This consumer AI-PC case package targets Windows; run it on Windows or use --mode dry-run")
    if args.mode == "execute" and paths["dut"].name.endswith("placeholder"):
        issues.append("--dut-root or AI_SSD_DUT_ROOT is required for execute mode")
    if _inside(paths["results_root"], paths["dut"]):
        issues.append("results root must not be inside the DUT root")
    if case.destructive and not args.confirm_destructive:
        issues.append("destructive case requires --confirm-destructive")
    if "PowerShell" in case.requirements and not _powershell():
        issues.append("PowerShell executable not found")
    if "Docker Desktop" in case.requirements and not _tool_exists("docker"):
        issues.append("docker executable not found")
    return issues


def _run_one(command: Sequence[str], *, run_dir: Path, label: str, args: argparse.Namespace) -> dict[str, object]:
    env = os.environ.copy()
    pythonpath = [str(REPO_ROOT), str(REPO_ROOT / "vdb_benchmark")]
    if env.get("PYTHONPATH"):
        pythonpath.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath)
    started = time.time()
    result: dict[str, object] = {
        "label": label,
        "command": list(command),
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    if args.mode != "execute":
        result.update({"status": "DRY_RUN", "returncode": None, "duration_seconds": 0.0})
        return result
    stdout_path = run_dir / f"{label}.stdout.log"
    stderr_path = run_dir / f"{label}.stderr.log"
    try:
        completed = subprocess.run(
            list(command), cwd=str(REPO_ROOT), env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", check=False,
        )
        stdout_path.write_text(completed.stdout or "", encoding="utf-8")
        stderr_path.write_text(completed.stderr or "", encoding="utf-8")
        result.update({
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "returncode": completed.returncode,
            "duration_seconds": round(time.time() - started, 3),
            "stdout": str(stdout_path),
            "stderr": str(stderr_path),
        })
    except OSError as error:
        stderr_path.write_text(str(error), encoding="utf-8")
        result.update({"status": "FAIL", "returncode": None, "duration_seconds": round(time.time() - started, 3), "stderr": str(stderr_path), "error": str(error)})
    return result


def _run_monitored(command: Sequence[str], *, run_dir: Path, label: str, args: argparse.Namespace) -> dict[str, object]:
    if not args.monitor:
        return _run_one(command, run_dir=run_dir, label=label, args=args)
    if os.name != "nt" or not PS1.is_file():
        return {"label": label, "status": "NOT_RUN", "returncode": None, "reason": "Windows monitor requested but record_windows_io.ps1 is unavailable"}
    powershell = _powershell()
    if not powershell:
        return {"label": label, "status": "NOT_RUN", "returncode": None, "reason": "PowerShell not found"}
    trace_dir = run_dir / "windows_io"
    trace_dir.mkdir(parents=True, exist_ok=True)
    wrapper = [
        powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(PS1),
        "-Name", f"{label}", "-CommandPath", str(command[0]), "-OutputDir", str(trace_dir),
        "-CommandArgumentList",
    ] + list(command[1:])
    return _run_one(wrapper, run_dir=run_dir, label=label, args=args)


def run_case(case_id: str, argv: Iterable[str] | None = None) -> int:
    case = get_case(case_id)
    parser = _parser(case)
    args = parser.parse_args(list(argv) if argv is not None else None)
    paths = _resolve_paths(args, case)
    run_id = f"{case.case_id}_{_now()}"
    run_dir = args.results_root / case.case_id / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "case": asdict(case),
        "run_id": run_id,
        "args": {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()},
        "paths": {key: str(value) for key, value in paths.items()},
        "host": {"platform": platform.platform(), "python": sys.version, "cwd": str(Path.cwd())},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    _json_dump(run_dir / "manifest.json", manifest)

    issues = _preflight(case, args, paths)
    if issues and args.mode == "execute":
        verdict = {"case_id": case.case_id, "run_id": run_id, "status": "NOT_RUN", "reasons": issues, "pass_criteria": case.pass_criteria}
        _json_dump(run_dir / "verdict.json", verdict)
        print(json.dumps(verdict, ensure_ascii=False, indent=2))
        return 2

    for path in (paths["dut"], paths["data"], paths["cache"], paths["checkpoint"]):
        if args.mode != "preflight":
            path.mkdir(parents=True, exist_ok=True)

    try:
        commands = _build_commands(args, paths, run_dir, case)
    except (FileNotFoundError, RuntimeError) as error:
        reason = str(error)
        verdict = {"case_id": case.case_id, "run_id": run_id, "status": "NOT_RUN", "reasons": [reason], "pass_criteria": case.pass_criteria}
        _json_dump(run_dir / "verdict.json", verdict)
        print(json.dumps(verdict, ensure_ascii=False, indent=2))
        return 2

    if args.mode == "preflight":
        verdict = {"case_id": case.case_id, "run_id": run_id, "status": "PREFLIGHT", "issues": issues, "commands": commands, "pass_criteria": case.pass_criteria}
        _json_dump(run_dir / "verdict.json", verdict)
        print(json.dumps(verdict, ensure_ascii=False, indent=2))
        return 0 if not issues else 2

    results: list[dict[str, object]] = []
    if case.kind in {"mix_kv_checkpoint", "mix_training_checkpoint", "soak_mixed"}:
        if args.mode != "execute":
            results.extend(
                {
                    "label": f"parallel_{index}",
                    "command": list(command),
                    "status": "DRY_RUN",
                    "returncode": None,
                    "duration_seconds": 0.0,
                }
                for index, command in enumerate(commands, start=1)
            )
        else:
            processes: list[tuple[subprocess.Popen[str], Path, Path]] = []
            env = os.environ.copy()
            env["PYTHONPATH"] = os.pathsep.join([str(REPO_ROOT), str(REPO_ROOT / "vdb_benchmark"), env.get("PYTHONPATH", "")])
            for index, command in enumerate(commands, start=1):
                out_path = run_dir / f"parallel_{index}.stdout.log"
                err_path = run_dir / f"parallel_{index}.stderr.log"
                out = out_path.open("w", encoding="utf-8")
                err = err_path.open("w", encoding="utf-8")
                processes.append((subprocess.Popen(command, cwd=str(REPO_ROOT), env=env, stdout=out, stderr=err, text=True), out_path, err_path))
            for index, (process, out_path, err_path) in enumerate(processes, start=1):
                rc = process.wait()
                results.append({"label": f"parallel_{index}", "status": "PASS" if rc == 0 else "FAIL", "returncode": rc, "stdout": str(out_path), "stderr": str(err_path)})
    else:
        for index, command in enumerate(commands, start=1):
            results.append(_run_monitored(command, run_dir=run_dir, label=f"command_{index}", args=args))

    status = "PASS" if results and all(item.get("status") == "PASS" for item in results) else "FAIL"
    if args.mode == "dry-run":
        status = "DRY_RUN"
    verdict = {
        "case_id": case.case_id,
        "run_id": run_id,
        "status": status,
        "pass_criteria": case.pass_criteria,
        "results": results,
        "issues": issues,
    }
    _json_dump(run_dir / "verdict.json", verdict)
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    return 0 if status in {"PASS", "DRY_RUN"} else 1


def main(case_id: str) -> int:
    return run_case(case_id)


def list_cases() -> list[str]:
    """Return case IDs in stable order for tooling and tests."""

    return sorted(CASES)
