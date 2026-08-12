from __future__ import annotations

import subprocess
import sys
from collections import Counter
from pathlib import Path

from full_test_plan_cases.catalog import SOURCE_SHA256, load_catalog


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_full_plan_contains_only_executable_native_cases() -> None:
    cases = load_catalog()

    assert len(cases) == 34
    assert [case["case_id"] for case in cases[:5]] == [
        "AI-TRN-003",
        "AI-TRN-004",
        "AI-TRN-005",
        "AI-CKP-001",
        "AI-CKP-002",
    ]
    assert cases[-1]["case_id"] == "AI-TRN-DLRM"
    assert Counter(case["family"] for case in cases) == {
        "Training": 4,
        "Checkpoint": 7,
        "KV Cache": 8,
        "VectorDB": 15,
    }
    assert SOURCE_SHA256 == "fada60afe5124244551ce248d3e8e3149a57a5b1b25bed2bc212d860d1d27656"


def test_every_case_has_native_commands_in_catalog() -> None:
    cases = load_catalog()

    for case in cases:
        assert case["native_status"] == "SUPPORTED"
        commands = case["native_commands"]
        assert commands, case["case_id"]
        assert all(command["argv"][0] == "open" for command in commands)


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


def test_run_case_plans_training_with_model_positional_and_prepare(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "full_test_plan_cases.run_case",
            "AI-TRN-003",
            "--mode",
            "plan",
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


def test_run_all_forwards_to_run_case_and_fast_fails(monkeypatch) -> None:
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
    assert calls[0][2] == "full_test_plan_cases.run_case"
    assert calls[0][3] == "AI-TRN-001"


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
    assert len(calls) >= 2  # init + at least one phase
    init_command, _ = calls[0]
    assert init_command[1] == "init"
    assert init_command[2] == "ai-kv-005-native"
    assert init_command[3] == str((tmp_path / "results" / "AI-KV-005").resolve())
    phase_command, phase_kwargs = calls[1]
    assert phase_command[0].endswith("mlpstorage.exe")
    assert "open" in phase_command
    assert "kvcache" in phase_command
    assert phase_kwargs["cwd"] == REPO_ROOT


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

    # KV cases carry the data-dir-derived --cache-dir instead of --data-dir
    assert default_command[default_command.index("--results-dir") + 1].startswith("C:\\")
    assert default_command[default_command.index("--cache-dir") + 1].startswith("C:\\")
    assert overridden_command[overridden_command.index("--results-dir") + 1].startswith("D:\\")
    assert overridden_command[overridden_command.index("--cache-dir") + 1].startswith("D:\\")


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
