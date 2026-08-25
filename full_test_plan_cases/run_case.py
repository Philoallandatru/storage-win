"""Run one native FULL_TEST_PLAN case directly from the catalog.

The 33 case entrypoints in ``full_test_plan_cases/cases/`` have been merged
into this single executor: the native command lists live in
``case_catalog.json`` (``native_commands``), and this module owns the
placeholder substitution, results-dir init, per-phase execution and data
cleanup that the case files used to duplicate 33 times.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from full_test_plan_cases.catalog import get_case, load_catalog


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = Path(__file__).with_name("site_config.json")
CAPACITY_CONFIG = Path(__file__).with_name("capacity_catalog.json")

_CAPACITY: dict | None = None


def _capacity_catalog() -> dict:
    """Load the 1TB/2TB capacity case catalog (lazy)."""
    global _CAPACITY
    if _CAPACITY is None:
        _CAPACITY = json.loads(CAPACITY_CONFIG.read_text(encoding="utf-8"))
    return _CAPACITY


def resolve_case(case_id: str) -> tuple[dict, list[str], bool]:
    """Return (case, capacity_overrides, single_drive) for any case id.

    Plain ids resolve from case_catalog.json.  Ids ending in ``-1TB`` /
    ``-2TB`` resolve from capacity_catalog.json against their base case;
    those always run single-drive (CAP-03 bypassed) by design.
    """
    case_id_upper = case_id.upper()
    try:
        return get_case(case_id_upper), [], False
    except KeyError:
        pass
    for capacity, entries in _capacity_catalog().items():
        if str(capacity).startswith("_"):
            continue
        spec = entries.get(case_id_upper)
        if spec is None:
            continue
        base = get_case(spec["base"])
        return base, list(spec.get("overrides", [])), True
    raise KeyError(case_id_upper)


class SiteConfigError(ValueError):
    """Raised when the one-time site configuration is invalid."""


def load_site_config(path: Path) -> dict[str, Any]:
    """Load and minimally validate the one-time site configuration."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise SiteConfigError(f"Site config not found: {path}") from error
    except json.JSONDecodeError as error:
        raise SiteConfigError(f"Invalid JSON in site config {path}: {error}") from error
    if not isinstance(payload, dict):
        raise SiteConfigError(f"Site config must be a JSON object: {path}")
    if "test_root" in payload:
        if not isinstance(payload.get("test_root"), str) or not payload["test_root"].strip():
            raise SiteConfigError("Site config requires a non-empty 'test_root'")
    else:
        for key in ("data_root", "results_root"):
            if not isinstance(payload.get(key), str) or not payload[key].strip():
                raise SiteConfigError(f"Site config requires a non-empty '{key}'")
    return payload


def _configured_path(config: dict[str, Any], key: str) -> Path:
    raw = os.path.expandvars(str(config[key]))
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def _normalize_drive(value: str) -> str:
    drive = str(value).strip().rstrip("\\/")
    if len(drive) == 1 and drive.isalpha():
        drive = f"{drive.upper()}:"
    if len(drive) != 2 or drive[0].isalpha() is False or drive[1] != ":":
        raise SiteConfigError(f"test_drive must be a Windows drive such as C or D:, got: {value}")
    return drive.upper()


def _replace_drive(path: Path, drive: str) -> Path:
    if not path.drive:
        return path
    tail = str(path)[len(path.drive) :].lstrip("\\/")
    return Path(f"{drive}\\") / tail


def _test_roots(config: dict[str, Any], drive_override: str | None) -> tuple[Path, Path]:
    """Resolve data/results roots from one drive, with legacy root compatibility."""
    if "test_root" not in config:
        data_root = _configured_path(config, "data_root")
        results_root = _configured_path(config, "results_root")
        if drive_override:
            drive = _normalize_drive(drive_override)
            data_root = _replace_drive(data_root, drive)
            results_root = _replace_drive(results_root, drive)
        return data_root, results_root

    drive = _normalize_drive(drive_override or str(config.get("test_drive", "C")))
    test_root_value = os.path.expandvars(str(config.get("test_root", "MLPerfStorageTest")))
    test_root = Path(test_root_value).expanduser()
    if test_root.is_absolute():
        test_root = _replace_drive(test_root, drive)
    else:
        test_root = Path(f"{drive}\\") / test_root
    test_root = test_root.resolve()
    data_root = test_root / str(config.get("data_subdir", "data"))
    results_root = test_root / str(config.get("results_subdir", "results"))
    return data_root.resolve(), results_root.resolve()


def _find_mlpstorage(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit
    for candidate in (Path(sys.executable).with_name("mlpstorage.exe"), Path(sys.executable).with_name("mlpstorage")):
        if candidate.is_file():
            return candidate
    return Path(shutil.which("mlpstorage") or "mlpstorage")


class Overrides:
    """Runtime overrides applied on top of the site config."""

    def __init__(
        self,
        *,
        mode: str = "execute",
        systemname: str | None = None,
        data_dir: Path | None = None,
        results_dir: Path | None = None,
        num_files_train: int | None = None,
        num_processes: int | None = None,
        num_checkpoints_write: int | None = None,
        num_checkpoints_read: int | None = None,
        num_vectors: int | None = None,
        num_accelerators: int | None = None,
        num_users: int | None = None,
        generation_mode: str | None = None,
        exec_type: str | None = None,
        cpu_mem_gb: int | None = None,
        trials: int | None = None,
        inter_option_delay: int | None = None,
        milvus_uri: str | None = None,
        vdb_config: Path | None = None,
        allow_invalid_params: bool = False,
        skip_fs_separation_gate: bool = False,
        keep_data: bool = False,
        mlpstorage: Path | None = None,
    ) -> None:
        self.mode = mode
        self.systemname = systemname
        self.data_dir = data_dir
        self.results_dir = results_dir
        self.num_files_train = num_files_train
        self.num_processes = num_processes
        self.num_checkpoints_write = num_checkpoints_write
        self.num_checkpoints_read = num_checkpoints_read
        self.num_vectors = num_vectors
        self.num_accelerators = num_accelerators
        self.num_users = num_users
        self.generation_mode = generation_mode
        self.exec_type = exec_type
        self.cpu_mem_gb = cpu_mem_gb
        self.trials = trials
        self.inter_option_delay = inter_option_delay
        self.milvus_uri = milvus_uri
        self.vdb_config = vdb_config
        self.allow_invalid_params = allow_invalid_params
        self.skip_fs_separation_gate = skip_fs_separation_gate
        self.keep_data = keep_data
        self.mlpstorage = mlpstorage


def _build_commands(
    case: dict[str, Any],
    *,
    data_dir: Path,
    results_dir: Path,
    systemname: str,
    mpi_bin: str,
    client_memory_gb: int,
    accelerators: int,
    query_processes: int,
    duration_sec: int,
    loops: int,
    prepare: bool,
    overrides: Overrides,
    vdb_data_dir: Path | None = None,
) -> list[list[str]]:
    """Resolve the case's native_commands into concrete mlpstorage argv lists.

    ``vdb_data_dir`` is used only by MIX cases: the VectorDB stream runs on a
    separate data drive (default E:) while the KV Cache stream runs on the
    primary ``data_dir`` (default C:).  Non-MIX cases ignore it.
    """
    values = {
        "<DATA_DIR>": str(data_dir.resolve()),
        "<RESULTS_DIR>": str(results_dir.resolve()),
        "<CHECKPOINT_DIR>": str(data_dir.resolve() / "checkpoint" / case["case_id"]),
        "<CACHE_DIR>": str(data_dir.resolve() / "kvcache" / case["case_id"]),
        "<STORAGE_ROOT>": str(data_dir.resolve() / "milvus" / case["case_id"]),
        # MIX dual-drive placeholders: KV stream on the primary data drive,
        # VDB stream on the secondary drive (default E:).
        "<MIX_KV_CACHE_DIR>": str(data_dir.resolve() / "kvcache" / case["case_id"]),
        "<MIX_VDB_STORAGE_ROOT>": str(
            (vdb_data_dir or data_dir).resolve() / "milvus" / case["case_id"]
        ),
        "<SYSTEMNAME>": systemname,
        "<CLIENT_MEMORY_GB>": str(client_memory_gb),
        "<ACCELERATORS>": str(overrides.num_accelerators if overrides.num_accelerators is not None else accelerators),
        "<QUERY_PROCESSES>": str(query_processes),
        "<DURATION_SEC>": str(duration_sec),
        "<LOOPS>": str(loops),
        "<MPI_BIN>": mpi_bin,
    }
    commands: list[list[str]] = []
    streams: list[str | None] = []
    for item in case.get("native_commands") or []:
        if item.get("phase") == "prepare" and not prepare:
            continue
        streams.append(item.get("stream"))
        argv = [values.get(a, a) for a in item["argv"] if a != "<COMMAND>"]
        # dataset.num_files_train lives inside --params KEY=VALUE tokens
        if overrides.num_files_train is not None:
            argv = [
                f"dataset.num_files_train={overrides.num_files_train}"
                if a.startswith("dataset.num_files_train=")
                else a
                for a in argv
            ]
        if overrides.vdb_config is not None and any(a == "vectordb" for a in argv):
            argv.extend(["--config", str(overrides.vdb_config)])
        if overrides.milvus_uri and "--host" in argv:
            host_i = argv.index("--host")
            argv = argv[:host_i] + argv[host_i + 2 :]
            argv.append("--milvus-uri")
            argv.append(overrides.milvus_uri)
        # generic flag -> value overrides (shrink dev runs)
        for flag, value in (
            ("--num-processes", overrides.num_processes),
            ("--num-checkpoints-write", overrides.num_checkpoints_write),
            ("--num-checkpoints-read", overrides.num_checkpoints_read),
            ("--num-vectors", overrides.num_vectors),
            ("--num-users", overrides.num_users),
            ("--generation-mode", overrides.generation_mode),
            ("--exec-type", overrides.exec_type),
            ("--cpu-mem-gb", overrides.cpu_mem_gb),
            ("--trials", overrides.trials),
            ("--inter-option-delay", overrides.inter_option_delay),
        ):
            if value is not None and flag in argv:
                argv[argv.index(flag) + 1] = str(value)
        if overrides.skip_fs_separation_gate:
            argv.append("--skip-fs-separation-gate")
        if overrides.allow_invalid_params:
            argv.append("--allow-invalid-params")
        commands.append(argv)
    return commands, streams


def build_case_command(
    case_id: str,
    config: dict[str, Any],
    *,
    python_executable: Path | None = None,
    mode_override: str | None = None,
    keep_data: bool = False,
    drive_override: str | None = None,
    data_dir_override: Path | None = None,
    results_dir_override: Path | None = None,
    num_files_train: int | None = None,
    allow_invalid_params: bool = False,
    skip_fs_separation_gate: bool = False,
) -> list[str]:
    """Return the first concrete mlpstorage command (backwards-compatible view)."""
    case = get_case(case_id)
    if case.get("native_status") != "SUPPORTED":
        raise SiteConfigError(f"{case_id} is not native-supported: {case.get('native_block_reason')}")
    data_root, results_root = _test_roots(config, drive_override)
    data_dir = data_dir_override or data_root / case_id
    results_dir = results_dir_override or results_root / case_id
    overrides = Overrides(
        mode=mode_override or "execute",
        data_dir=data_dir if data_dir_override else None,
        results_dir=results_dir if results_dir_override else None,
        num_files_train=num_files_train,
        allow_invalid_params=allow_invalid_params,
        skip_fs_separation_gate=skip_fs_separation_gate,
        keep_data=keep_data,
    )
    commands, _streams = _build_commands(
        case,
        data_dir=data_dir,
        results_dir=results_dir,
        systemname=str(config.get("systemname", f"{case_id.lower()}-native")),
        mpi_bin=str(config.get("mpi_bin", "mpiexec")),
        client_memory_gb=int(config.get("client_memory_gb", 64)),
        accelerators=int(config.get("accelerators", 1)),
        query_processes=int(config.get("query_processes", 1)),
        duration_sec=int(config.get("duration_sec", 60)),
        loops=int(config.get("loops", 1)),
        prepare=bool(config.get("prepare", True)),
        overrides=overrides,
    )
    if not commands:
        raise SiteConfigError(f"no executable command for {case_id}")
    python = python_executable or Path(sys.executable)
    return [str(python), "-m", "mlpstorage_py.main", *commands[0]]


def _apply_capacity_overrides(overrides: Overrides, duration_sec: int, capacity_overrides: list[str], cli_duration_sec: int | None = None) -> int:
    """Apply capacity-catalog overrides (CLI-style flag/value pairs).

    Dev (CLI) overrides take precedence: a flag already set on the command
    line is never overwritten by the capacity tier, so ``--num-files-train 8``
    still shrinks a ``-1TB`` capacity case on a small disk.
    """
    for i in range(0, len(capacity_overrides) - 1, 2):
        flag, value = capacity_overrides[i], capacity_overrides[i + 1]
        if flag == "--duration-sec":
            if cli_duration_sec is None:
                duration_sec = int(value)
        elif flag == "--num-files-train" and overrides.num_files_train is None:
            overrides.num_files_train = int(value)
        elif flag == "--num-processes" and overrides.num_processes is None:
            overrides.num_processes = int(value)
        elif flag == "--num-accelerators" and overrides.num_accelerators is None:
            overrides.num_accelerators = int(value)
        elif flag == "--num-checkpoints-write" and overrides.num_checkpoints_write is None:
            overrides.num_checkpoints_write = int(value)
        elif flag == "--num-checkpoints-read" and overrides.num_checkpoints_read is None:
            overrides.num_checkpoints_read = int(value)
        elif flag == "--num-vectors" and overrides.num_vectors is None:
            overrides.num_vectors = int(value)
        elif flag == "--trials" and overrides.trials is None:
            overrides.trials = int(value)
        elif flag == "--inter-option-delay" and overrides.inter_option_delay is None:
            overrides.inter_option_delay = int(value)
    return duration_sec


def _venv_path_env() -> dict:
    """Copy os.environ with ``.venv/Scripts`` prepended to PATH.

    Mirrors the PATH injection ``run_case.cmd`` / ``scripts/cases/*.cmd``
    do, so mlpstorage child processes (and via them ``dlio_benchmark``,
    ``load-vdb``, …) resolve console scripts no matter which entry point
    launched this module (cmd, PowerShell, bash, or python -m directly).
    """
    env = os.environ.copy()
    scripts = str(REPO_ROOT / ".venv" / "Scripts")
    env["PATH"] = scripts + os.pathsep + env.get("PATH", "")
    return env


def _run_mlpstorage(cli: Path, argv: list[str]) -> int:
    command = [str(cli), *argv]
    print(f"mlpstorage {' '.join(argv[:6])} ... (see phase output)", flush=True)
    completed = subprocess.run(command, cwd=REPO_ROOT, check=False, env=_venv_path_env())
    return completed.returncode


def _cleanup(data_dir: Path, cleanup_root: Path) -> None:
    data_path = data_dir.resolve()
    root_path = cleanup_root.resolve()
    if data_path == root_path:
        print(f"CLEANUP_FAILED: data-dir ({data_path}) is the cleanup root itself")
        print(f"  Refusing to delete the data root (safety guard). Pass a case subdirectory,")
        print(f"  e.g. --data-dir {root_path}\\<CASE_ID>, or omit --data-dir to let the case")
        print(f"  directory be derived automatically.")
        return
    if root_path not in data_path.parents:
        print(f"CLEANUP_FAILED: data path is outside cleanup root: {data_path}")
        print(f"  cleanup root is {root_path}; only paths below it are deleted.")
        print(f"  Check for stray characters (e.g. '<', '>', '|') in the --data-dir argument.")
        return
    if data_path.exists():
        shutil.rmtree(data_path)
    print(f"TEST_DATA_ROOT={data_path}")
    print(f"TEST_DATA_CLEANED={not data_path.exists()}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run one native MLPerf Storage case directly from the catalog",
        epilog="Normal use: run_case.cmd AI-KV-005",
    )
    parser.add_argument("case_id", help="Case ID, for example AI-KV-005")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--mode", choices=("plan", "preflight", "dry-run", "execute"), default=None)
    parser.add_argument("--test-drive", help="Override the configured single Windows test drive, for example D:")
    parser.add_argument("--data-dir", type=Path, help="Override data directory (must be a different filesystem than results)")
    parser.add_argument("--results-dir", type=Path, help="Override results directory (must be a different filesystem than data)")
    parser.add_argument("--num-files-train", type=int, help="Dev: override dataset.num_files_train (training cases)")
    parser.add_argument("--num-processes", type=int, help="Dev: override --num-processes (checkpoint ranks / datagen workers)")
    parser.add_argument("--num-checkpoints-write", type=int, help="Dev: override --num-checkpoints-write")
    parser.add_argument("--num-checkpoints-read", type=int, help="Dev: override --num-checkpoints-read")
    parser.add_argument("--num-vectors", type=int, help="Dev: override --num-vectors (vectordb datagen)")
    parser.add_argument("--num-users", type=int, help="Dev: override --num-users (kvcache; shrinks the CAP-01 disk-space floor)")
    parser.add_argument("--generation-mode", choices=("none", "fast", "realistic"), default=None,
                        help="Dev: override --generation-mode (kvcache; fast = 15x quicker smoke)")
    parser.add_argument("--exec-type", choices=("mpi", "single"), default=None,
                        help="Dev: override --exec-type (training/checkpoint; single avoids Windows DLIO MPI finalize abort)")
    parser.add_argument("--cpu-mem-gb", type=int, default=None,
                        help="Dev: override --cpu-mem-gb (kvcache CPU-memory tier size)")
    parser.add_argument("--trials", type=int, help="Dev: override --trials (kvcache)")
    parser.add_argument("--inter-option-delay", type=int, help="Dev: override --inter-option-delay (kvcache)")
    parser.add_argument("--milvus-uri", help="Dev: use a local Milvus Lite .db path instead of --host/--port (vectordb)")
    parser.add_argument("--vdb-config", type=Path, help="Dev: use a shrunk vdbbench config YAML for vectordb cases")
    parser.add_argument("--mix-vdb-data-dir", type=Path, default=None,
                        help="Dev (MIX only): data dir for the VectorDB stream (default: E: drive)")
    parser.add_argument("--allow-invalid-params", "-aip", action="store_true", help="Dev: let mlpstorage run with invalid (e.g. shrunk) params")
    parser.add_argument("--skip-fs-separation-gate", action="store_true", help="Dev: bypass CAP-03 same-filesystem gate")
    parser.add_argument("--keep-data", action="store_true")
    parser.add_argument("--print-command", action="store_true")
    # site-config overrides (accepted by run_ai_ssd_suite.py forwarding)
    parser.add_argument("--launcher", choices=("single", "mpi"), default=None)
    parser.add_argument("--mpi-bin", choices=("mpiexec", "mpirun"), default=None)
    parser.add_argument("--systemname", default=None)
    parser.add_argument("--mlpstorage", type=Path, default=None)
    parser.add_argument("--prepare", action="store_true", default=None)
    parser.add_argument("--confirm-dut", action="store_true", default=None)
    parser.add_argument("--init-results", action="store_true", default=None)
    parser.add_argument("--cleanup-data", action="store_true", default=None)
    parser.add_argument("--cleanup-root", type=Path, default=None)
    parser.add_argument("--loops", type=int, default=None)
    parser.add_argument("--duration-sec", type=int, default=None)
    parser.add_argument("--accelerators", type=int, default=None)
    parser.add_argument("--client-memory-gb", type=int, default=None)
    parser.add_argument("--query-processes", type=int, default=None)
    parser.add_argument("--dlio-bin-path", type=Path, default=None)
    parser.add_argument("--o-direct", action="store_true", default=None)
    args = parser.parse_args()

    try:
        case, capacity_overrides, single_drive = resolve_case(args.case_id)
    except KeyError as error:
        print(f"Unknown case ID: {args.case_id}", file=sys.stderr)
        return 2

    try:
        config = load_site_config(args.config.resolve())
    except SiteConfigError as error:
        print(f"Configuration error: {error}", file=sys.stderr)
        return 2

    if case.get("native_status") != "SUPPORTED":
        print(f"{args.case_id.upper()} BLOCKED: {case.get('native_block_reason')}")
        return 2

    data_root, results_root = _test_roots(config, args.test_drive)
    data_dir = (args.data_dir or (data_root / args.case_id)).resolve()
    results_dir = (args.results_dir or (results_root / args.case_id)).resolve()
    systemname = args.systemname or str(config.get("systemname", f"{args.case_id.lower()}-native"))
    mode = args.mode or str(config.get("mode", "execute"))
    mpi_bin = args.mpi_bin or str(config.get("mpi_bin", "mpiexec"))
    prepare = args.prepare if args.prepare is not None else bool(config.get("prepare", True))
    if single_drive:
        # 1TB/2TB capacity cases are designed to run on a single drive.
        args.skip_fs_separation_gate = True
    cleanup_data = (
        args.cleanup_data if args.cleanup_data is not None else bool(config.get("cleanup_data", True))
    ) and not args.keep_data
    cleanup_root = args.cleanup_root or data_root
    init_results = args.init_results if args.init_results is not None else bool(config.get("init_results", True))
    confirm_dut = args.confirm_dut if args.confirm_dut is not None else bool(config.get("confirm_dut", True))

    duration_sec = args.duration_sec or int(config.get("duration_sec", 60))
    overrides = Overrides(
        mode=mode,
        data_dir=args.data_dir,
        results_dir=args.results_dir,
        num_files_train=args.num_files_train,
        num_processes=args.num_processes,
        num_checkpoints_write=args.num_checkpoints_write,
        num_checkpoints_read=args.num_checkpoints_read,
        num_vectors=args.num_vectors,
        num_users=args.num_users,
        generation_mode=args.generation_mode,
        exec_type=args.exec_type,
        cpu_mem_gb=args.cpu_mem_gb,
        trials=args.trials,
        inter_option_delay=args.inter_option_delay,
        milvus_uri=args.milvus_uri,
        vdb_config=args.vdb_config,
        allow_invalid_params=args.allow_invalid_params,
        skip_fs_separation_gate=args.skip_fs_separation_gate,
        keep_data=args.keep_data,
        mlpstorage=args.mlpstorage or (Path(str(config["mlpstorage"])) if config.get("mlpstorage") else None),
    )

    # MIX cases run the VectorDB stream on a separate data drive (default E:).
    if case.get("family") == "MIX":
        mix_vdb_dir = args.mix_vdb_data_dir
        if mix_vdb_dir is None:
            # Same default as run_ai_ssd_suite.py --vdb-drive; the suite
            # normally passes an explicit dir, this is the bare-CLI fallback.
            mix_vdb_dir = Path("E:") / str(config.get("test_root", "MLPerfStorageTest")) / "data"
        vdb_data_dir = mix_vdb_dir
    else:
        vdb_data_dir = None

    commands, streams = _build_commands(
        case,
        data_dir=data_dir,
        results_dir=results_dir,
        systemname=systemname,
        mpi_bin=mpi_bin,
        client_memory_gb=args.client_memory_gb or int(config.get("client_memory_gb", 64)),
        accelerators=args.accelerators or int(config.get("accelerators", 1)),
        query_processes=args.query_processes or int(config.get("query_processes", 1)),
        duration_sec=duration_sec,
        loops=args.loops or int(config.get("loops", 1)),
        prepare=prepare,
        overrides=overrides,
        vdb_data_dir=vdb_data_dir,
    )
    if capacity_overrides:
        duration_sec = _apply_capacity_overrides(overrides, duration_sec, capacity_overrides, cli_duration_sec=args.duration_sec)
        commands, streams = _build_commands(
            case, data_dir=data_dir, results_dir=results_dir, systemname=systemname,
            mpi_bin=mpi_bin,
            client_memory_gb=args.client_memory_gb or int(config.get("client_memory_gb", 64)),
            accelerators=args.accelerators or int(config.get("accelerators", 1)),
            query_processes=args.query_processes or int(config.get("query_processes", 1)),
            duration_sec=duration_sec,
            loops=args.loops or int(config.get("loops", 1)),
            prepare=prepare, overrides=overrides,
            vdb_data_dir=vdb_data_dir,
        )
    if args.o_direct:
        for argv in commands:
            if not any(a == "--o-direct" for a in argv):
                argv.append("--o-direct")
    if args.dlio_bin_path:
        for argv in commands:
            argv.extend(["--dlio-bin-path", str(args.dlio_bin_path)])

    cli = _find_mlpstorage(overrides.mlpstorage)
    display = [str(Path(sys.executable)), "-m", "mlpstorage_py.main", *commands[0]]
    print(f"CASE={args.case_id.upper()}")
    print(f"COMMAND={subprocess.list2cmdline(display)}")
    if args.print_command:
        return 0

    if mode in ("plan", "preflight"):
        for argv in commands:
            print(f"mlpstorage {' '.join(argv)}")
        return 0
    if mode == "dry-run":
        for argv in commands:
            print(f"mlpstorage {' '.join(argv)} --dry-run")
        return 3

    # execute mode
    if not confirm_dut:
        print(f"{args.case_id.upper()} BLOCKED: confirm_dut is disabled in site config")
        return 2
    results_dir.parent.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)  # E401: training/checkpoint need the data root to exist
    # Pre-create per-case subdirs so CAP-01/CAP-03/E401 probes find their parents
    # (checkpoint-folder / kvcache cache-dir / vectordb storage-root).
    for sub in ("checkpoint", "kvcache", "milvus"):
        (data_dir / sub / case["case_id"]).mkdir(parents=True, exist_ok=True)
    if vdb_data_dir is not None:
        # MIX: VectorDB stream lives on the secondary drive (E:) — pre-create
        # its storage root too so E401/CAP-01 probes have a parent.
        (vdb_data_dir / "milvus" / case["case_id"]).mkdir(parents=True, exist_ok=True)
    if init_results:
        init_command = [str(cli), "init", systemname, str(results_dir)]
        print(f"{args.case_id} init: {subprocess.list2cmdline(init_command)}")
        initialized = subprocess.run(init_command, check=False, env=_venv_path_env())
        if initialized.returncode != 0:
            return initialized.returncode

    # MIX cases run the KV Cache stream (C:) and VectorDB stream (E:)
    # concurrently; each stream's phases still run in order.
    def _run_phases(stream_cmds: list[list[str]], stream_name: str | None = None) -> int:
        prefix = f"[{stream_name}] " if stream_name else ""
        for si, argv in enumerate(stream_cmds, start=1):
            print(f"{args.case_id} {prefix}phase {si}/{len(stream_cmds)}: "
                  f"mlpstorage {' '.join(argv[:8])} ...")
            rc = _run_mlpstorage(cli, argv)
            if rc != 0:
                print(f"{args.case_id} {prefix}FAIL phase={si} rc={rc}")
                return rc
        return 0

    if any(streams):
        stream_groups: dict[str, list[list[str]]] = {}
        for stream, argv in zip(streams, commands):
            stream_groups.setdefault(stream or "main", []).append(argv)
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(stream_groups)) as pool:
            futures = {pool.submit(_run_phases, cmds, name): name
                       for name, cmds in stream_groups.items()}
            rc = 0
            for fut in concurrent.futures.as_completed(futures):
                name = futures[fut]
                try:
                    stream_rc = fut.result()
                except Exception as exc:  # pragma: no cover - defensive
                    print(f"{args.case_id} [{name}] EXCEPTION: {exc}")
                    stream_rc = 1
                if stream_rc != 0:
                    rc = stream_rc
        if rc != 0:
            if cleanup_data:
                _cleanup(data_dir, cleanup_root)
            return rc
    else:
        rc = _run_phases(commands)
        if rc != 0:
            if cleanup_data:
                _cleanup(data_dir, cleanup_root)
            return rc

    if cleanup_data:
        _cleanup(data_dir, cleanup_root)
    print(f"{args.case_id} PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
