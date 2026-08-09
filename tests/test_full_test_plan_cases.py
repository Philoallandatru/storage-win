from __future__ import annotations

import subprocess
import sys
from collections import Counter
from pathlib import Path

from full_test_plan_cases.catalog import SOURCE_SHA256, load_catalog


REPO_ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = REPO_ROOT / "full_test_plan_cases" / "cases"


def _filename(case_id: str) -> str:
    return f"test_{case_id.lower().replace('-', '_')}.py"


def test_full_plan_has_all_72_cases_in_workbook_order() -> None:
    cases = load_catalog()

    assert len(cases) == 72
    assert [case["case_id"] for case in cases[:5]] == [
        "AI-BASE-001",
        "AI-BASE-002",
        "AI-BASE-003",
        "AI-BASE-004",
        "AI-TRN-001",
    ]
    assert cases[-1]["case_id"] == "AI-MIX-005"
    assert Counter(case["family"] for case in cases) == {
        "Base": 4,
        "Training": 16,
        "Checkpoint": 9,
        "KV Cache": 22,
        "VectorDB": 16,
        "Mixed": 5,
    }
    assert SOURCE_SHA256 == "fada60afe5124244551ce248d3e8e3149a57a5b1b25bed2bc212d860d1d27656"


def test_each_case_has_a_self_contained_entrypoint() -> None:
    expected = {_filename(case["case_id"]) for case in load_catalog()}
    actual = {path.name for path in CASE_DIR.glob("test_*.py")}

    assert actual == expected
    for path in sorted(CASE_DIR.glob("test_*.py")):
        source = path.read_text(encoding="utf-8")
        assert "subprocess.run" in source
        assert "full_test_plan_cases.runner" not in source


def test_catalog_keeps_workbook_command_separate_from_native_command() -> None:
    training = next(case for case in load_catalog() if case["case_id"] == "AI-TRN-003")
    mixed = next(case for case in load_catalog() if case["case_id"] == "AI-MIX-001")

    assert "--model unet3d" in training["workbook_command"]
    assert "open training unet3d datagen file" in training["source_command"]
    assert training["native_status"] == "SUPPORTED"
    assert mixed["native_status"] == "BLOCKED"
    assert "no native" in mixed["source_command"].lower()


def test_native_training_plan_uses_model_positional_and_optional_prepare(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(CASE_DIR / "test_ai_trn_003.py"),
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
    assert "mlpstorage open training unet3d datagen file" in completed.stdout
    assert "mlpstorage open training unet3d run file" in completed.stdout


def test_run_all_forwards_to_case_files_and_fast_fails(monkeypatch) -> None:
    import full_test_plan_cases.run_all as run_all

    calls: list[list[str]] = []

    class Completed:
        returncode = 7

    monkeypatch.setattr(run_all, "load_catalog", lambda: [
        {"case_id": "AI-TRN-001", "family": "Training", "priority": "P1"},
        {"case_id": "AI-TRN-002", "family": "Training", "priority": "P1"},
    ])

    def fake_run(command, **_kwargs):
        calls.append(command)
        return Completed()

    monkeypatch.setattr(run_all.subprocess, "run", fake_run)
    monkeypatch.setattr(run_all.sys, "argv", [
        "run_all.py",
        "--mode",
        "execute",
        "--confirm-dut",
    ])

    assert run_all.main() == 1
    assert len(calls) == 1
    assert calls[0][1].endswith("full_test_plan_cases\\cases\\test_ai_trn_001.py")
    assert "full_test_plan_cases.runner" not in " ".join(calls[0])
