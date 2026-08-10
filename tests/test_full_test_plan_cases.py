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


def test_full_plan_contains_only_executable_native_cases() -> None:
    cases = load_catalog()

    assert len(cases) == 33
    assert [case["case_id"] for case in cases[:5]] == [
        "AI-TRN-003",
        "AI-TRN-004",
        "AI-TRN-005",
        "AI-CKP-001",
        "AI-CKP-002",
    ]
    assert cases[-1]["case_id"] == "AI-VDB-016"
    assert Counter(case["family"] for case in cases) == {
        "Training": 3,
        "Checkpoint": 7,
        "KV Cache": 8,
        "VectorDB": 15,
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

    assert "--model unet3d" in training["workbook_command"]
    assert "open training unet3d datagen file" in training["source_command"]
    assert "dataset.num_files_train=7200" in training["source_command"]
    assert training["native_status"] == "SUPPORTED"
    assert all(
        command["argv"][0] == "open"
        for case in load_catalog()
        for command in case["native_commands"]
    )


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


def test_case_supports_native_results_init_and_data_cleanup_flags(tmp_path: Path) -> None:
    source = (CASE_DIR / "test_ai_trn_003.py").read_text(encoding="utf-8")

    assert "--init-results" in source
    assert "--cleanup-data" in source
    assert "--cleanup-root" in source


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


def test_run_case_needs_only_case_id_and_uses_site_config(monkeypatch, tmp_path: Path) -> None:
    import full_test_plan_cases.run_case as run_case

    calls: list[tuple[list[str], dict[str, object]]] = []
    config = {
        "mode": "execute",
        "data_root": str(tmp_path / "dut"),
        "results_root": str(tmp_path / "results"),
        "launcher": "mpi",
        "mpi_bin": "mpiexec",
        "mlpstorage": str(tmp_path / "venv" / "mlpstorage.exe"),
        "duration_sec": 60,
        "loops": 1,
        "client_memory_gb": 64,
        "accelerators": 1,
        "query_processes": 1,
        "prepare": True,
        "confirm_dut": True,
        "init_results": True,
        "cleanup_data": True,
    }

    class Completed:
        returncode = 0

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return Completed()

    monkeypatch.setattr(run_case, "load_site_config", lambda _path: config)
    monkeypatch.setattr(run_case.subprocess, "run", fake_run)
    monkeypatch.setattr(run_case.sys, "argv", ["run_case.py", "AI-KV-005"])

    assert run_case.main() == 0
    assert len(calls) == 1
    command, kwargs = calls[0]
    assert command[1].endswith("full_test_plan_cases\\cases\\test_ai_kv_005.py")
    assert command[command.index("--mode") + 1] == "execute"
    assert command[command.index("--data-dir") + 1] == str((tmp_path / "dut" / "AI-KV-005").resolve())
    assert command[command.index("--results-dir") + 1] == str((tmp_path / "results" / "AI-KV-005").resolve())
    assert "--confirm-dut" in command
    assert "--prepare" in command
    assert "--init-results" in command
    assert "--cleanup-data" in command
    assert command[command.index("--cleanup-root") + 1] == str((tmp_path / "dut").resolve())
    assert kwargs["cwd"] == REPO_ROOT


def test_run_case_uses_one_default_drive_and_accepts_drive_override(tmp_path: Path) -> None:
    import full_test_plan_cases.run_case as run_case

    config = {
        "test_drive": "C",
        "test_root": "MLPerfStorageTest",
        "launcher": "mpi",
        "mpi_bin": "mpiexec",
        "mlpstorage": str(tmp_path / "venv" / "mlpstorage.exe"),
        "confirm_dut": True,
        "init_results": True,
        "cleanup_data": True,
    }

    default_command = run_case.build_case_command("AI-KV-005", config, python_executable=tmp_path / "python.exe")
    overridden_command = run_case.build_case_command(
        "AI-KV-005",
        config,
        python_executable=tmp_path / "python.exe",
        drive_override="D",
    )

    assert default_command[default_command.index("--data-dir") + 1].startswith("C:\\")
    assert default_command[default_command.index("--results-dir") + 1].startswith("C:\\")
    assert overridden_command[overridden_command.index("--data-dir") + 1].startswith("D:\\")
    assert overridden_command[overridden_command.index("--results-dir") + 1].startswith("D:\\")


def test_run_case_rejects_unknown_case_before_spawning(monkeypatch) -> None:
    import full_test_plan_cases.run_case as run_case

    monkeypatch.setattr(run_case.sys, "argv", ["run_case.py", "AI-NOT-REAL"])
    monkeypatch.setattr(
        run_case,
        "load_site_config",
        lambda _path: {"data_root": "D:/dut", "results_root": "C:/results"},
    )

    assert run_case.main() == 2


def test_windows_run_case_launcher_has_one_argument_interface() -> None:
    launcher = REPO_ROOT / "run_case.cmd"

    source = launcher.read_text(encoding="utf-8")
    assert "-m full_test_plan_cases.run_case %*" in source
    assert ".venv\\Scripts\\python.exe" in source
