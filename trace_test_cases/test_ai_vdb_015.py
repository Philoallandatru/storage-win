"""AI-VDB-015: capture a formal Milvus trace and replay it on the DUT.

The commands executed here are the repository's native ``vdbbench`` entry
points.  This file only supplies case parameters, evidence, and cleanup; it
does not implement another benchmark engine.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from vdbbench.replay import load_trace, replay_trace


CASE_ID = "AI-VDB-015"
DEFAULT_CONFIG = Path("vdb_benchmark/vdbbench/benchmark/configs/windows_trace_smoke.yaml")


def _command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def _capture_command(args: argparse.Namespace) -> list[str]:
    executable = shutil.which("vdbbench-modular")
    if executable:
        return [
            executable,
            "--config", str(args.config),
            "--io-trace-log", str(args.source_trace),
            "--output-dir", str(args.source_results),
        ]
    return [
        sys.executable,
        "-m", "vdbbench.benchmark.run_benchmark",
        "--config", str(args.config),
        "--io-trace-log", str(args.source_trace),
        "--output-dir", str(args.source_results),
    ]


def _replay_command(args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        "-m", "vdbbench.replay",
        str(args.source_trace),
        "--data-dir", str(args.data_dir),
    ]
    if args.direct_io:
        command.append("--direct-io")
    if args.as_fast_as_possible:
        command.append("--as-fast-as-possible")
    return command


def _safe_cleanup(data_dir: Path, cleanup_root: Path) -> None:
    data_resolved = data_dir.resolve()
    root_resolved = cleanup_root.resolve()
    if data_resolved == root_resolved or root_resolved not in data_resolved.parents:
        raise RuntimeError(
            f"refusing cleanup outside the approved root: data={data_resolved} root={root_resolved}"
        )
    if data_resolved.exists():
        shutil.rmtree(data_resolved)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"{CASE_ID} trace capture/replay")
    parser.add_argument("--mode", choices=("plan", "preflight", "execute"), default="plan")
    parser.add_argument("--record", action="store_true", help="run the formal Milvus source workload first")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--source-trace", type=Path, required=True)
    parser.add_argument("--source-results", type=Path, default=Path("results/ai-vdb-015-source"))
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--cleanup", action="store_true")
    parser.add_argument("--cleanup-root", type=Path)
    parser.add_argument("--direct-io", action="store_true")
    parser.add_argument("--as-fast-as-possible", action="store_true")
    parser.add_argument("--confirm-dut", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    capture = _capture_command(args)
    replay = _replay_command(args)
    print("CAPTURE:", subprocess.list2cmdline(capture))
    print("REPLAY:", subprocess.list2cmdline(replay))

    if args.mode == "plan":
        return 0
    if args.mode == "execute" and not args.confirm_dut:
        print(f"{CASE_ID} BLOCKED: execute requires --confirm-dut")
        return 2
    if args.cleanup and args.cleanup_root is None:
        print(f"{CASE_ID} BLOCKED: --cleanup requires --cleanup-root")
        return 2
    if args.mode == "preflight":
        if args.record and not args.config.is_file():
            print(f"{CASE_ID} BLOCKED: config not found: {args.config}")
            return 2
        if not args.record and not args.source_trace.is_file():
            print(f"{CASE_ID} BLOCKED: source trace not found: {args.source_trace}")
            return 2
        if not _command_exists("vdbbench-modular"):
            print("vdbbench-modular not on PATH; module fallback will be used")
        if args.source_trace.is_file():
            events = load_trace(args.source_trace)
            print(f"TRACE_VALID=True events={len(events)}")
        return 0

    args.data_dir.mkdir(parents=True, exist_ok=True)
    args.results_dir.mkdir(parents=True, exist_ok=True)
    exit_code = 0
    try:
        if args.record:
            completed = subprocess.run(capture, check=False)
            if completed.returncode != 0:
                return completed.returncode
        events = load_trace(args.source_trace)
        summary = replay_trace(
            trace_path=args.source_trace,
            data_dir=args.data_dir,
            direct_io=args.direct_io,
            respect_timing=not args.as_fast_as_possible,
        )
        evidence = {
            "case_id": CASE_ID,
            "mode": "TRACE-CAPTURE+TRACE-REPLAY" if args.record else "TRACE-REPLAY",
            "source_trace": str(args.source_trace.resolve()),
            "event_count": len(events),
            "summary": asdict(summary),
        }
        (args.results_dir / "trace_replay_summary.json").write_text(
            json.dumps(evidence, indent=2), encoding="utf-8"
        )
        print(json.dumps(evidence, indent=2))
        print(f"{CASE_ID} CONDITIONAL")
    except Exception as error:
        print(f"{CASE_ID} FAIL: {error}")
        exit_code = 1
    finally:
        if args.cleanup:
            try:
                _safe_cleanup(args.data_dir, args.cleanup_root)
                print(f"TEST_DATA_ROOT={args.data_dir.resolve()}")
                print("TEST_DATA_CLEANED=True")
            except Exception as error:
                print(f"CLEANUP_FAILED: {error}")
                exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

