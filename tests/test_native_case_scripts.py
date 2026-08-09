from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = REPO_ROOT / "full_test_plan_cases" / "cases"
AI_CASE_DIR = REPO_ROOT / "ai_ssd_test_cases"


def _plan(case_file: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CASE_DIR / case_file),
            "--mode",
            "plan",
            "--data-dir",
            "D:/dut",
            "--results-dir",
            "E:/results",
            "--prepare",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_training_case_prints_native_model_before_command() -> None:
    completed = _plan("test_ai_trn_003.py")

    assert completed.returncode == 0, completed.stderr
    assert "mlpstorage open training unet3d datagen file" in completed.stdout
    assert "mlpstorage open training unet3d run file" in completed.stdout
    assert "--model unet3d" not in completed.stdout
    assert "--exec-type mpi" in completed.stdout
    assert "--exec-type docker" not in completed.stdout
    assert "runner.py" not in completed.stdout


def test_checkpoint_case_prints_native_model_flag_and_real_rank_count() -> None:
    completed = _plan("test_ai_ckp_003.py")

    assert completed.returncode == 0, completed.stderr
    assert "mlpstorage open checkpointing run file" in completed.stdout
    assert "--model llama3-70b" in completed.stdout
    assert "--num-processes 64" in completed.stdout
    assert "--model llama3-70b-full-64-ranks" not in completed.stdout


def test_distributed_checkpoint_cannot_run_with_single_process_launcher(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(CASE_DIR / "test_ai_ckp_003.py"),
            "--mode",
            "preflight",
            "--launcher",
            "single",
            "--data-dir",
            str(tmp_path / "dut"),
            "--results-dir",
            str(tmp_path / "results"),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert "requires --launcher mpi" in completed.stdout


def test_native_cli_unsupported_case_is_blocked_instead_of_simulated() -> None:
    completed = _plan("test_ai_mix_001.py")

    assert completed.returncode == 2
    assert "BLOCKED" in completed.stdout
    assert "native mlpstorage command" in completed.stdout
    assert "SMOKE_PASS" not in completed.stdout


def test_case_scripts_do_not_delegate_runtime_to_the_old_runner() -> None:
    scripts = sorted(CASE_DIR.glob("test_*.py"))

    assert len(scripts) == 72
    for script in scripts:
        source = script.read_text(encoding="utf-8")
        assert "from full_test_plan_cases.runner import run_case" not in source
        assert "mlpstorage init" not in source
        assert "subprocess.run" in source


def test_ai_ssd_case_alias_is_also_direct_native(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(AI_CASE_DIR / "test_training_unet3d_a100_baseline.py"),
            "--mode",
            "plan",
            "--prepare",
            "--data-dir",
            str(tmp_path / "dut"),
            "--results-dir",
            str(tmp_path / "results"),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "mlpstorage whatif training unet3d datagen file" in completed.stdout
    assert "runner_support" not in completed.stdout


def test_ai_catalog_exposes_native_status_and_commands() -> None:
    catalog = json.loads((AI_CASE_DIR / "case_catalog.json").read_text(encoding="utf-8"))

    assert len(catalog) == 72
    assert catalog["AI-TRN-003"]["native_status"] == "SUPPORTED"
    assert "open training unet3d datagen file" in catalog["AI-TRN-003"]["source_command"]
    assert catalog["AI-MIX-001"]["native_status"] == "BLOCKED"
    assert catalog["AI-MIX-001"]["native_commands"] == []
