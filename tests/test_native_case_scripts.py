"""All 33 native cases must plan (produce concrete mlpstorage commands) from
the unified executor driven by case_catalog.json — no per-case entrypoints."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from full_test_plan_cases.catalog import load_catalog


REPO_ROOT = Path(__file__).resolve().parents[1]


def _plan(case_id: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "full_test_plan_cases.run_case",
            case_id,
            "--mode",
            "plan",
            "--data-dir",
            "D:/dut",
            "--results-dir",
            "E:/results",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_every_catalog_case_plans_from_the_unified_executor() -> None:
    cases = load_catalog()
    assert len(cases) == 34
    failed = []
    for case in cases:
        completed = _plan(case["case_id"])
        if completed.returncode != 0 or "mlpstorage open" not in completed.stdout:
            failed.append(f"{case['case_id']} rc={completed.returncode}")
    assert failed == []


def test_training_case_prints_native_model_positional_command() -> None:
    completed = _plan("AI-TRN-003")

    assert completed.returncode == 0, completed.stderr
    assert "mlpstorage open training unet3d datagen file" in completed.stdout
    assert "mlpstorage open training unet3d run file" in completed.stdout
    assert "--model unet3d" not in completed.stdout
    assert "--exec-type mpi" in completed.stdout
    assert "--exec-type docker" not in completed.stdout


def test_checkpoint_case_prints_native_model_flag_and_real_rank_count() -> None:
    completed = _plan("AI-CKP-003")

    assert completed.returncode == 0, completed.stderr
    assert "mlpstorage open checkpointing run file" in completed.stdout
    assert "--model llama3-70b" in completed.stdout
    assert "--num-processes 64" in completed.stdout


def test_dev_overrides_flow_into_planned_commands() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "full_test_plan_cases.run_case",
            "AI-TRN-003",
            "--mode",
            "plan",
            "--data-dir",
            "D:/dut",
            "--results-dir",
            "E:/results",
            "--num-files-train",
            "8",
            "--allow-invalid-params",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "dataset.num_files_train=8" in completed.stdout
    assert "--allow-invalid-params" in completed.stdout
