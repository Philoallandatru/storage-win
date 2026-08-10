"""Run one native FULL_TEST_PLAN case from a site-level configuration."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from full_test_plan_cases.catalog import get_case


REPO_ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = REPO_ROOT / "full_test_plan_cases" / "cases"
DEFAULT_CONFIG = Path(__file__).with_name("site_config.json")


class SiteConfigError(ValueError):
    """Raised when the one-time site configuration is invalid."""


def _case_filename(case_id: str) -> str:
    return f"test_{case_id.lower().replace('-', '_')}.py"


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


def build_case_command(
    case_id: str,
    config: dict[str, Any],
    *,
    python_executable: Path | None = None,
    mode_override: str | None = None,
    keep_data: bool = False,
) -> list[str]:
    """Build the independent case entrypoint command from site defaults."""
    case = get_case(case_id)
    normalized = case["case_id"]
    case_file = CASE_DIR / _case_filename(normalized)
    if not case_file.is_file():
        raise SiteConfigError(f"Case entrypoint is missing: {case_file}")

    mode = mode_override or str(config.get("mode", "execute"))
    if mode not in {"plan", "preflight", "dry-run", "execute"}:
        raise SiteConfigError(f"Unsupported mode in site config: {mode}")
    if mode == "execute" and not bool(config.get("confirm_dut", True)):
        raise SiteConfigError("execute mode requires confirm_dut=true in site config")

    data_root = _configured_path(config, "data_root")
    results_root = _configured_path(config, "results_root")
    data_dir = data_root / normalized
    results_dir = results_root / normalized
    python = python_executable or Path(sys.executable)

    command = [
        str(python),
        str(case_file),
        "--mode",
        mode,
        "--data-dir",
        str(data_dir),
        "--results-dir",
        str(results_dir),
        "--launcher",
        str(config.get("launcher", "mpi")),
        "--mpi-bin",
        str(config.get("mpi_bin", "mpiexec" if os.name == "nt" else "mpirun")),
        "--systemname",
        str(config.get("systemname", f"{normalized.lower()}-native")),
        "--duration-sec",
        str(config.get("duration_sec", 60)),
        "--loops",
        str(config.get("loops", 1)),
        "--client-memory-gb",
        str(config.get("client_memory_gb", 64)),
        "--accelerators",
        str(config.get("accelerators", 1)),
        "--query-processes",
        str(config.get("query_processes", 1)),
    ]
    mlpstorage = config.get("mlpstorage")
    if mlpstorage:
        command.extend(["--mlpstorage", str(_configured_path(config, "mlpstorage"))])
    dlio_bin_path = config.get("dlio_bin_path")
    if dlio_bin_path:
        command.extend(["--dlio-bin-path", str(_configured_path(config, "dlio_bin_path"))])
    for flag, enabled in (
        ("--prepare", config.get("prepare", True)),
        ("--confirm-dut", config.get("confirm_dut", True)),
        ("--init-results", config.get("init_results", True)),
        ("--o-direct", config.get("o_direct", False)),
    ):
        if enabled:
            command.append(flag)
    if config.get("cleanup_data", True) and not keep_data:
        command.extend(["--cleanup-data", "--cleanup-root", str(data_root)])
    return command


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run one configured native MLPerf Storage case",
        epilog="Normal use: run_case.cmd AI-KV-005",
    )
    parser.add_argument("case_id", help="Case ID, for example AI-KV-005")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--mode", choices=("plan", "preflight", "dry-run", "execute"))
    parser.add_argument("--keep-data", action="store_true")
    parser.add_argument("--print-command", action="store_true")
    args = parser.parse_args()

    try:
        get_case(args.case_id)
    except KeyError:
        print(f"Unknown case ID: {args.case_id}", file=sys.stderr)
        return 2
    try:
        config = load_site_config(args.config.resolve())
        command = build_case_command(
            args.case_id,
            config,
            mode_override=args.mode,
            keep_data=args.keep_data,
        )
    except SiteConfigError as error:
        print(f"Configuration error: {error}", file=sys.stderr)
        return 2

    display = subprocess.list2cmdline(["python", *command[1:]])
    print(f"CASE={args.case_id.upper()}")
    print(f"COMMAND={display}")
    if args.print_command:
        return 0

    env = os.environ.copy()
    scripts_dir = str(Path(sys.executable).resolve().parent)
    env["PATH"] = scripts_dir + os.pathsep + env.get("PATH", "")
    completed = subprocess.run(command, cwd=REPO_ROOT, env=env, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
