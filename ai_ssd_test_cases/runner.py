"""Unified Python runner for the legacy AI SSD execution matrix.

The runner has two deliberate behaviors:

* Cases with a current native MLPerf entry delegate to that entrypoint and
  preserve its real return code and evidence.
* Cases without a current native entry can run only when the caller explicitly
  supplies ``--scale-mb``.  Those workloads exercise the requested storage
  pattern with Python, but their verdict is marked ``formal_status``
  ``NOT_FORMAL`` so a scaled result cannot be confused with an MLPerf result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import shutil
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .catalog import CASES, CaseSpec, get_case


REPO_ROOT = Path(__file__).resolve().parents[1]
NATIVE_CASE_DIR = REPO_ROOT / "full_test_plan_cases" / "cases"
TRN001_ENTRY = REPO_ROOT / "tools" / "run_ai_trn_001_windows.py"
TRACE_ENTRY = REPO_ROOT / "trace_test_cases" / "test_ai_vdb_015.py"
DEFAULT_TRACE = REPO_ROOT / "full_test_plan_cases" / "fixtures" / "logical_io_smoke.csv"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _json_dump(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
        description=f"Execute {case.case_id}: {case.family} / {case.profile}",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--execute", action="store_true", help="authorize the real workload")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--result-dir", "--results-dir", dest="result_dir", type=Path, required=True)
    parser.add_argument("--prepare", action="store_true", help="run native datagen before the workload")
    parser.add_argument("--confirm-dut", action="store_true", help="explicitly confirm the DUT path")
    parser.add_argument("--cleanup-data", action="store_true")
    parser.add_argument("--cleanup-root", type=Path)
    parser.add_argument("--keep-data", action="store_true")
    parser.add_argument("--launcher", choices=("single", "mpi"), default="single")
    parser.add_argument("--mpi-bin", choices=("mpiexec", "mpirun"), default="mpiexec" if os.name == "nt" else "mpirun")
    parser.add_argument("--systemname", default=None)
    parser.add_argument("--client-memory-gb", type=int, default=64)
    parser.add_argument("--accelerators", type=int, default=1)
    parser.add_argument("--query-processes", type=int, default=1)
    parser.add_argument("--duration-sec", type=int, default=60)
    parser.add_argument("--loops", type=int, default=1)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--users", type=int, default=25)
    parser.add_argument("--scale-mb", type=int, default=None, help="explicit scaled Python workload size")
    parser.add_argument("--direct", "--o-direct", dest="direct", action="store_true")
    parser.add_argument("--monitor", action="store_true", help="capture Windows PhysicalDisk counters when available")
    parser.add_argument("--backend", choices=("remote", "lite"), default="remote")
    parser.add_argument("--source-trace", type=Path, default=None)
    parser.add_argument("--trace-config", type=Path, default=None)
    parser.add_argument("--full", action="store_true", help="allow a formal-sized operation when data already exists")
    return parser


def _validate(args: argparse.Namespace, case: CaseSpec) -> list[str]:
    issues: list[str] = []
    data_dir = args.data_dir.resolve()
    result_dir = args.result_dir.resolve()
    if not args.execute:
        issues.append("--execute is required; planning and dry-run modes are not execution")
    if os.name != "nt":
        issues.append("this matrix targets native Windows; WSL is not supported")
    if _inside(result_dir, data_dir):
        issues.append("result directory must not be inside the DUT data directory")
    if args.cleanup_data:
        if args.keep_data:
            issues.append("--cleanup-data and --keep-data cannot be combined")
        if args.cleanup_root is None:
            issues.append("--cleanup-data requires --cleanup-root")
        elif data_dir == args.cleanup_root.resolve() or not _inside(data_dir, args.cleanup_root.resolve()):
            issues.append("data directory must be strictly inside --cleanup-root")
    if case.destructive and not args.confirm_dut:
        issues.append("destructive case requires --confirm-dut")
    if case.execution == "python_scaled" and args.scale_mb is None:
        issues.append("this case has no formal native entry; pass --scale-mb explicitly for a Python scaled run")
    if case.family == "VectorDB" and args.backend == "lite" and args.scale_mb is None:
        issues.append("--backend lite requires --scale-mb so the local database size is explicit")
    if args.scale_mb is not None and args.scale_mb <= 0:
        issues.append("--scale-mb must be positive")
    if args.duration_sec <= 0 or args.repeat <= 0 or args.users <= 0:
        issues.append("duration, repeat, and users must be positive")
    return issues


def _native_entry(case: CaseSpec) -> Path:
    if case.execution == "native_special":
        return TRN001_ENTRY
    assert case.native_case_id
    filename = f"test_{case.native_case_id.lower().replace('-', '_')}.py"
    return NATIVE_CASE_DIR / filename


def build_command(
    case_id: str,
    *,
    data_dir: Path,
    results_dir: Path,
    prepare: bool = False,
    launcher: str = "single",
    mpi_bin: str | None = None,
    systemname: str | None = None,
    client_memory_gb: int = 64,
    accelerators: int = 1,
    query_processes: int = 1,
    duration_sec: int = 60,
    loops: int = 1,
    direct: bool = False,
) -> list[str]:
    """Build the real native command without executing it."""

    case = get_case(case_id)
    if case.execution not in {"native", "native_special"}:
        raise ValueError(f"{case.case_id} has no current native command; use --scale-mb for Python fallback")
    entry = _native_entry(case)
    if not entry.is_file():
        raise FileNotFoundError(f"native entrypoint is missing: {entry}")
    command = [sys.executable, str(entry), "--data-dir", _path_text(data_dir), "--results-dir", _path_text(results_dir)]
    if case.execution == "native_special":
        command.extend(
            [
                "--mpi-bin",
                mpi_bin or ("mpiexec" if os.name == "nt" else "mpirun"),
                "--systemname",
                systemname or f"{case.case_id.lower()}-legacy",
                "--client-memory-gb",
                str(client_memory_gb),
                "--accelerators",
                str(accelerators),
                "--loops",
                str(loops),
                "--confirm-dut",
            ]
        )
    else:
        command.extend(
            [
                "--launcher",
                launcher,
                "--mpi-bin",
                mpi_bin or ("mpiexec" if os.name == "nt" else "mpirun"),
                "--systemname",
                systemname or f"{case.case_id.lower()}-legacy",
                "--client-memory-gb",
                str(client_memory_gb),
                "--accelerators",
                str(accelerators),
                "--query-processes",
                str(query_processes),
                "--duration-sec",
                str(duration_sec),
                "--loops",
                str(loops),
                "--confirm-dut",
            ]
        )
    if prepare:
        command.append("--prepare")
    if direct:
        command.append("--o-direct")
    return command


def _monitor_start(run_dir: Path, enabled: bool) -> tuple[subprocess.Popen[str] | None, Path | None]:
    if not enabled or os.name != "nt" or shutil.which("typeperf") is None:
        return None, None
    output = run_dir / "windows_physicaldisk.csv"
    command = [
        "typeperf",
        r"\PhysicalDisk(*)\Disk Read Bytes/sec",
        r"\PhysicalDisk(*)\Disk Write Bytes/sec",
        r"\PhysicalDisk(*)\Avg. Disk sec/Read",
        r"\PhysicalDisk(*)\Current Disk Queue Length",
        "-si",
        "1",
        "-o",
        str(output),
    ]
    return subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, text=True), output


def _monitor_stop(handle: subprocess.Popen[str] | None) -> None:
    if handle is None:
        return
    handle.terminate()
    try:
        handle.wait(timeout=5)
    except subprocess.TimeoutExpired:
        handle.kill()
        handle.wait(timeout=5)


def _payload(size: int) -> bytes:
    chunk = b"MLPERF-STORAGE-AI-SSD\0"
    repeats = math.ceil(size / len(chunk))
    return (chunk * repeats)[:size]


def _read_file(path: Path, chunk_size: int = 1024 * 1024) -> int:
    total = 0
    with path.open("rb", buffering=0) as stream:
        while True:
            block = stream.read(chunk_size)
            if not block:
                return total
            total += len(block)


def _file_profile(data_dir: Path, *, scale_mb: int, profile: str) -> dict[str, Any]:
    data_dir.mkdir(parents=True, exist_ok=True)
    root = data_dir / "python_scaled"
    root.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    requested_bytes = scale_mb * 1024 * 1024
    operations = 0
    bytes_read = 0
    bytes_written = 0

    if "small" in profile or "metadata" in profile:
        count = max(16, min(4096, scale_mb * 16))
        item = _payload(max(1024, requested_bytes // count))
        paths = [root / f"sample_{index:06d}.bin" for index in range(count)]
        for path in paths:
            path.write_bytes(item)
            bytes_written += len(item)
        for path in paths:
            path.stat()
            with path.open("rb") as stream:
                bytes_read += len(stream.read())
            operations += 1
    else:
        path = root / "sequential.bin"
        path.write_bytes(_payload(requested_bytes))
        bytes_written = requested_bytes
        if "random" in profile or "shuffle" in profile:
            with path.open("rb", buffering=0) as stream:
                for offset in range(0, requested_bytes, max(4096, requested_bytes // 32)):
                    stream.seek(offset)
                    bytes_read += len(stream.read(min(1024 * 1024, requested_bytes - offset)))
                    operations += 1
        else:
            bytes_read = _read_file(path)
            operations = 1
    elapsed = max(time.perf_counter() - started, 1e-9)
    return {
        "profile": profile,
        "bytes_read": bytes_read,
        "bytes_written": bytes_written,
        "operations": operations,
        "elapsed_seconds": round(elapsed, 6),
        "read_mib_per_second": round(bytes_read / 1024 / 1024 / elapsed, 3),
        "write_mib_per_second": round(bytes_written / 1024 / 1024 / elapsed, 3),
        "formal_status": "NOT_FORMAL",
    }


def _run_base(case: CaseSpec, args: argparse.Namespace) -> dict[str, Any]:
    data_dir = args.data_dir.resolve()
    result_dir = args.result_dir.resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(data_dir)
    result: dict[str, Any] = {
        "profile": case.profile,
        "data_dir": str(data_dir),
        "result_dir": str(result_dir),
        "disk_free_bytes": usage.free,
        "paths_separated": not _inside(result_dir, data_dir),
        "formal_status": "CONDITIONAL",
    }
    if case.profile == "path_capacity":
        result["physical_disk_inventory"] = _physical_disk_inventory()
        return result
    if args.scale_mb is None:
        raise RuntimeError("BASE cache/repeatability workloads require --scale-mb")
    if case.profile == "cache_modes":
        result["buffered_warm"] = _file_profile(data_dir, scale_mb=args.scale_mb, profile="buffered_warm")
        result["cold_reopen"] = _file_profile(data_dir, scale_mb=args.scale_mb, profile="buffered_cold")
        result["direct"] = {"status": "UNSUPPORTED", "reason": "native Windows direct-I/O alignment is not inferred automatically"}
        return result
    if case.profile == "repeatability":
        samples = [_file_profile(data_dir, scale_mb=args.scale_mb, profile="repeatability") for _ in range(max(3, args.repeat))]
        values = [float(item["read_mib_per_second"]) for item in samples]
        mean = statistics.mean(values)
        cv = statistics.pstdev(values) / mean if mean else float("inf")
        result["runs"] = samples
        result["throughput_cv"] = round(cv, 6)
        result["monitor_requested"] = args.monitor
        return result
    if case.profile == "fill_degradation":
        if not args.confirm_dut:
            raise RuntimeError("fill-level degradation requires --confirm-dut")
        result["scaled_fill_level"] = True
        result["measurement"] = _file_profile(data_dir, scale_mb=args.scale_mb, profile="fill_level")
        return result
    raise RuntimeError(f"unknown BASE profile: {case.profile}")


def _physical_disk_inventory() -> dict[str, Any]:
    if os.name != "nt" or shutil.which("powershell") is None:
        return {"status": "UNAVAILABLE", "reason": "PowerShell is unavailable"}
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        "Get-PhysicalDisk | Select-Object FriendlyName,SerialNumber,HealthStatus,OperationalStatus,Size | ConvertTo-Json -Compress",
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode:
        return {"status": "ERROR", "returncode": completed.returncode, "stderr": completed.stderr.strip()}
    try:
        return {"status": "OK", "disks": json.loads(completed.stdout or "[]")}
    except json.JSONDecodeError:
        return {"status": "OK", "raw": completed.stdout.strip()}


def _run_checkpoint_scaled(args: argparse.Namespace, case: CaseSpec) -> dict[str, Any]:
    if args.scale_mb is None:
        raise RuntimeError("checkpoint fallback requires --scale-mb; it never shrinks a formal checkpoint silently")
    root = args.data_dir.resolve() / "python_scaled" / "checkpoint"
    root.mkdir(parents=True, exist_ok=True)
    payload = _payload(max(1024 * 1024, args.scale_mb * 1024 * 1024 // 8))
    hashes: list[str] = []
    started = time.perf_counter()
    for cycle in range(max(1, args.repeat)):
        cycle_hashes: list[str] = []
        for rank in range(8):
            path = root / f"{case.case_id.lower()}_cycle_{cycle:03d}_rank_{rank:03d}.bin"
            with path.open("wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            cycle_hashes.append(hashlib.sha256(path.read_bytes()).hexdigest())
        hashes.extend(cycle_hashes)
    elapsed = max(time.perf_counter() - started, 1e-9)
    return {
        "profile": case.profile,
        "cycles": max(1, args.repeat),
        "ranks": 8,
        "bytes_per_rank": len(payload),
        "hash_count": len(hashes),
        "hashes_consistent": len(set(hashes)) == 1,
        "elapsed_seconds": round(elapsed, 6),
        "formal_status": "NOT_FORMAL",
    }


def _run_kv_scaled(args: argparse.Namespace, case: CaseSpec) -> dict[str, Any]:
    if args.scale_mb is None:
        raise RuntimeError("KV fallback requires --scale-mb; use a current native KV case for formal MLPerf options")
    root = args.data_dir.resolve() / "python_scaled" / "kv_cache"
    root.mkdir(parents=True, exist_ok=True)
    entries = max(args.users, min(4096, args.scale_mb * 4))
    item = _payload(max(4096, args.scale_mb * 1024 * 1024 // entries))
    started = time.perf_counter()
    written = 0
    read = 0
    for index in range(entries):
        path = root / f"{case.case_id.lower()}_{index:06d}.kv"
        path.write_bytes(item)
        written += len(item)
    for index in range(entries):
        read += len((root / f"{case.case_id.lower()}_{index:06d}.kv").read_bytes())
    elapsed = max(time.perf_counter() - started, 1e-9)
    return {
        "profile": case.profile,
        "model_support": "PYTHON_PATTERN_ONLY",
        "entries": entries,
        "bytes_written": written,
        "bytes_read": read,
        "elapsed_seconds": round(elapsed, 6),
        "read_mib_per_second": round(read / 1024 / 1024 / elapsed, 3),
        "write_mib_per_second": round(written / 1024 / 1024 / elapsed, 3),
        "formal_status": "NOT_FORMAL",
    }


def _run_vdb_lite_scaled(args: argparse.Namespace, case: CaseSpec) -> dict[str, Any]:
    if args.scale_mb is None:
        raise RuntimeError("VectorDB fallback requires --scale-mb")
    try:
        from pymilvus import MilvusClient
    except ImportError as error:
        raise RuntimeError("PyMilvus and milvus-lite are required for --backend lite") from error
    root = args.data_dir.resolve() / "python_scaled" / "vectordb"
    root.mkdir(parents=True, exist_ok=True)
    db_path = root / f"{case.case_id.lower()}.db"
    collection = f"{case.case_id.lower().replace('-', '_')}_lite"
    dimension = 128
    count = max(16, min(5000, args.scale_mb * 32))
    vectors = []
    for index in range(count):
        vectors.append({"id": index, "vector": [float((index + offset) % 17) / 17.0 for offset in range(dimension)]})
    try:
        client = MilvusClient(str(db_path))
    except Exception as error:
        raise RuntimeError(
            "Milvus Lite is unavailable; install the Windows vectordb-milvus extra "
            "before using --backend lite"
        ) from error
    try:
        if client.has_collection(collection):
            client.drop_collection(collection)
        client.create_collection(collection, dimension=dimension, metric_type="COSINE")
        for start in range(0, len(vectors), 256):
            client.insert(collection, vectors[start : start + 256])
        hits = client.search(collection, data=[vectors[0]["vector"]], limit=10)
        top_id = hits[0][0]["id"] if hits and hits[0] else None
        return {
            "profile": case.profile,
            "backend": "milvus-lite",
            "requested_index": case.profile,
            "actual_index": "Milvus Lite default collection index",
            "dimension": dimension,
            "vectors": count,
            "top1_id": top_id,
            "query_succeeded": top_id == 0,
            "formal_status": "NOT_FORMAL",
        }
    finally:
        try:
            client.drop_collection(collection)
        finally:
            client.close()


def _run_mixed_scaled(args: argparse.Namespace, case: CaseSpec) -> dict[str, Any]:
    if args.scale_mb is None:
        raise RuntimeError("mixed fallback requires --scale-mb; native mixed orchestration is not inferred")
    profiles = ["mixed_training", "mixed_checkpoint", "mixed_kv"]
    if case.case_id == "AI-MIX-003":
        profiles.append("mixed_vdb")
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=len(profiles)) as pool:
        futures = [pool.submit(_file_profile, args.data_dir.resolve() / profile, scale_mb=args.scale_mb, profile=profile) for profile in profiles]
        results = [future.result() for future in futures]
    return {
        "profile": case.profile,
        "parallel_profiles": profiles,
        "results": results,
        "elapsed_seconds": round(time.perf_counter() - started, 6),
        "formal_status": "NOT_FORMAL",
    }


def _run_python_scaled(case: CaseSpec, args: argparse.Namespace) -> dict[str, Any]:
    if case.family == "Training":
        return _file_profile(args.data_dir.resolve(), scale_mb=args.scale_mb or 1, profile=case.profile)
    if case.family == "Checkpoint":
        return _run_checkpoint_scaled(args, case)
    if case.family == "KV Cache":
        return _run_kv_scaled(args, case)
    if case.family == "VectorDB":
        if args.backend != "lite":
            raise RuntimeError("non-native VectorDB cases require --backend lite for a Python-started Milvus Lite run")
        return _run_vdb_lite_scaled(args, case)
    if case.family == "Mixed":
        return _run_mixed_scaled(args, case)
    raise RuntimeError(f"no Python fallback for {case.case_id}")


def _trace_command(args: argparse.Namespace) -> list[str]:
    source_trace = (args.source_trace or DEFAULT_TRACE).resolve()
    if not source_trace.is_file():
        raise RuntimeError(f"AI-VDB-015 source trace not found: {source_trace}")
    if not TRACE_ENTRY.is_file():
        raise FileNotFoundError(f"trace entrypoint is missing: {TRACE_ENTRY}")
    command = [
        sys.executable,
        str(TRACE_ENTRY),
        "--source-trace",
        _path_text(source_trace),
        "--data-dir",
        _path_text(args.data_dir),
        "--results-dir",
        _path_text(args.result_dir),
        "--confirm-dut",
    ]
    if args.direct:
        command.append("--direct-io")
    return command


def _write_verdict(run_dir: Path, manifest: dict[str, Any], status: str, *, reason: str | None = None, result: object | None = None) -> int:
    manifest["status"] = status
    if reason:
        manifest["reason"] = reason
    if result is not None:
        manifest["result"] = result
    _json_dump(run_dir / "manifest.json", manifest)
    _json_dump(run_dir / "verdict.json", manifest)
    return 0 if status == "PASS" else 2 if status == "BLOCKED" else 1


def run_case(case_id: str, argv: Iterable[str] | None = None) -> int:
    case = get_case(case_id)
    parser = _parser(case)
    args = parser.parse_args(list(argv) if argv is not None else None)
    data_dir = args.data_dir.resolve()
    result_dir = args.result_dir.resolve()
    run_dir = result_dir / case.case_id / _now()
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "case_id": case.case_id,
        "family": case.family,
        "execution": case.execution,
        "profile": case.profile,
        "argv": list(argv) if argv is not None else sys.argv[1:],
        "paths": {"data_dir": str(data_dir), "result_dir": str(result_dir), "run_dir": str(run_dir)},
        "host": {"platform": platform.platform(), "python": sys.version, "cwd": str(Path.cwd())},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    issues = _validate(args, case)
    if issues:
        return _write_verdict(run_dir, manifest, "BLOCKED", reason="; ".join(issues))
    data_dir.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(parents=True, exist_ok=True)
    monitor, monitor_path = _monitor_start(run_dir, args.monitor)
    try:
        if case.family == "VectorDB" and args.backend == "lite":
            result = _run_vdb_lite_scaled(args, case)
            return _write_verdict(run_dir, manifest, "PASS", result=result)
        if case.execution in {"native", "native_special"}:
            command = build_command(
                case.case_id,
                data_dir=data_dir,
                results_dir=result_dir,
                prepare=args.prepare,
                launcher=args.launcher,
                mpi_bin=args.mpi_bin,
                systemname=args.systemname,
                client_memory_gb=args.client_memory_gb,
                accelerators=args.accelerators,
                query_processes=args.query_processes,
                duration_sec=args.duration_sec,
                loops=args.loops,
                direct=args.direct,
            )
            manifest["command"] = command
            completed = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, check=False, encoding="utf-8", errors="replace")
            (run_dir / "stdout.log").write_text(completed.stdout or "", encoding="utf-8")
            (run_dir / "stderr.log").write_text(completed.stderr or "", encoding="utf-8")
            if completed.returncode == 0:
                status = "PASS"
            elif completed.returncode == 3 or "CAP-01" in (completed.stdout + completed.stderr):
                status = "BLOCKED"
            else:
                status = "FAIL"
            reason = f"native command exited with {completed.returncode}" if status != "PASS" else None
            return _write_verdict(run_dir, manifest, status, reason=reason, result={"returncode": completed.returncode, "monitor": str(monitor_path) if monitor_path else None})
        if case.execution == "trace":
            command = _trace_command(args)
            manifest["command"] = command
            completed = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, check=False, encoding="utf-8", errors="replace")
            (run_dir / "stdout.log").write_text(completed.stdout or "", encoding="utf-8")
            (run_dir / "stderr.log").write_text(completed.stderr or "", encoding="utf-8")
            return _write_verdict(
                run_dir,
                manifest,
                "PASS" if completed.returncode == 0 else "FAIL",
                reason=None if completed.returncode == 0 else f"trace command exited with {completed.returncode}",
                result={"returncode": completed.returncode, "formal_status": "CONDITIONAL"},
            )
        if case.execution == "python_base":
            result = _run_base(case, args)
        else:
            result = _run_python_scaled(case, args)
        return _write_verdict(run_dir, manifest, "PASS", result=result)
    except (FileNotFoundError, RuntimeError, OSError, ValueError) as error:
        return _write_verdict(run_dir, manifest, "BLOCKED", reason=str(error))
    finally:
        _monitor_stop(monitor)
        if args.cleanup_data and not args.keep_data and data_dir.exists():
            shutil.rmtree(data_dir)


def main_from_filename(filename: str) -> int:
    path = Path(filename).resolve()
    for case in CASES.values():
        if (REPO_ROOT / case.entrypoint).resolve() == path:
            return run_case(case.case_id)
    raise SystemExit(f"No AI SSD case is registered for {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one legacy AI SSD case entrypoint")
    parser.add_argument("case_id", choices=sorted(CASES))
    args, rest = parser.parse_known_args()
    return run_case(args.case_id, rest)


if __name__ == "__main__":
    raise SystemExit(main())
