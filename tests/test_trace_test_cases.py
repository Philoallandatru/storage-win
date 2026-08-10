from __future__ import annotations

import subprocess
import sys
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CASE = REPO_ROOT / "trace_test_cases" / "test_ai_vdb_015.py"
TRACE = REPO_ROOT / "vdb_benchmark" / "results" / "formal_vdbbench_trace.csv"
CATALOG = REPO_ROOT / "trace_test_cases" / "catalog.json"


def test_trace_catalog_contains_only_executable_cases() -> None:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))

    assert [item["case_id"] for item in catalog] == ["AI-VDB-015"]
    assert all(item["status"] == "SUPPORTED" for item in catalog)


def test_vdb_trace_case_plan_contains_capture_and_replay() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(CASE),
            "--mode",
            "plan",
            "--source-trace",
            str(TRACE),
            "--data-dir",
            str(REPO_ROOT / "never-used-trace-data"),
            "--results-dir",
            str(REPO_ROOT / "never-used-trace-results"),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "vdbbench.benchmark.run_benchmark" in completed.stdout
    assert "vdbbench.replay" in completed.stdout


def test_vdb_trace_case_preflight_validates_source_trace() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(CASE),
            "--mode",
            "preflight",
            "--source-trace",
            str(TRACE),
            "--data-dir",
            str(REPO_ROOT / "never-used-trace-data"),
            "--results-dir",
            str(REPO_ROOT / "never-used-trace-results"),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "TRACE_VALID=True events=211" in completed.stdout
