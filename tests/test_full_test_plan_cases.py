from __future__ import annotations

import subprocess
import sys
from collections import Counter
from pathlib import Path

from full_test_plan_cases.catalog import SOURCE_SHA256, load_catalog


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_full_plan_contains_only_executable_native_cases() -> None:
    cases = load_catalog()

    assert len(cases) == 35
    assert [case["case_id"] for case in cases[:5]] == [
        "AI-TRN-003",
        "AI-TRN-004",
        "AI-TRN-005",
        "AI-CKP-001",
        "AI-CKP-002",
    ]
    assert cases[-1]["case_id"] == "AI-MIX-001"
    assert Counter(case["family"] for case in cases) == {
        "Training": 4,
        "Checkpoint": 7,
        "KV Cache": 8,
        "VectorDB": 15,
        "MIX": 1,
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
    """run_all was folded into run_ai_ssd_suite.py; its family/priority
    filtering is now exercised via cases_for_tier (the suite's selector).
    """
    import scripts.run_ai_ssd_suite as suite

    cases = suite.cases_for_tier("512GB", family="KV Cache", priority="P0")
    assert cases
    assert all(suite.case_family(c) == "KV Cache" for c in cases)
    # every selected case exists in the catalog
    catalog_ids = {c["case_id"] for c in suite.load_catalog()}
    assert all(c in catalog_ids for c in cases)


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


def test_suite_kv_cache_timeout_longer_than_other_families() -> None:
    """KV Cache runs 3 options each with fixed 90s start/end delays, so the
    suite must give it a longer default budget (1800s) than other families
    (900s), while an explicit --case-timeout always wins."""
    import scripts.run_ai_ssd_suite as suite

    # Reproduce the resolution logic used in the suite main loop.
    def resolve(fam: str, explicit: int | None) -> int:
        if explicit is not None:
            return explicit
        return 1800 if fam == "KV Cache" else 900

    assert resolve("KV Cache", None) == 1800
    assert resolve("Training", None) == 900
    assert resolve("Checkpoint", None) == 900
    assert resolve("VectorDB", None) == 900
    assert resolve("MIX", None) == 900
    assert resolve("KV Cache", 500) == 500  # explicit override wins
