"""Contract tests for the 72-case FULL_TEST_PLAN executable suite."""

from __future__ import annotations

import json
import subprocess
import sys
import types
from collections import Counter
from pathlib import Path

from full_test_plan_cases.catalog import SOURCE_SHA256, load_catalog
from full_test_plan_cases.runner import (
    RunOptions,
    build_workload_plan,
    classify_command_status,
    prepare_command_output_paths,
    run_case,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = REPO_ROOT / "full_test_plan_cases" / "cases"


def _filename(case_id: str) -> str:
    return f"test_{case_id.lower().replace('-', '_')}.py"


def test_runner_import_does_not_require_datetime_utc(monkeypatch) -> None:
    """The standalone case launcher must also import on Python 3.10."""
    import builtins
    import datetime as real_datetime
    import importlib.util

    datetime_without_utc = types.ModuleType("datetime")
    for name in dir(real_datetime):
        if name != "UTC":
            setattr(datetime_without_utc, name, getattr(real_datetime, name))

    real_import = builtins.__import__

    def import_without_utc(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "datetime":
            return datetime_without_utc
        return real_import(name, globals, locals, fromlist, level)

    module_name = "_full_test_plan_runner_datetime_compat"
    spec = importlib.util.spec_from_file_location(
        module_name,
        REPO_ROOT / "full_test_plan_cases" / "runner.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    monkeypatch.setattr(builtins, "__import__", import_without_utc)

    spec.loader.exec_module(module)


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
    assert (REPO_ROOT / "full_test_plan_cases" / "source" / "FULL_TEST_PLAN.xlsx").is_file()
    assert (REPO_ROOT / "full_test_plan_cases" / "source" / "FULL_TEST_PLAN.xlsx.inspect.ndjson").is_file()


def test_each_full_plan_case_has_one_case_id_entrypoint() -> None:
    expected = {_filename(case["case_id"]) for case in load_catalog()}
    actual = {
        path.name
        for path in CASE_DIR.glob("test_*.py")
        if path.name != "__init__.py"
    }

    assert actual == expected


def test_catalog_preserves_full_workbook_execution_fields() -> None:
    by_id = {case["case_id"]: case for case in load_catalog()}
    training = by_id["AI-TRN-001"]

    assert training["tool"] == "mlpstorage + DLIO + PowerShell 监控"
    assert "UNet3D/A100" in training["purpose"]
    assert "mlpstorage open training datagen file" in training["source_command"]
    assert "AU>=90%" in training["standard"]
    assert training["priority"] == "P1"
    assert training["profile"] == "X"
    assert training["windows_status"] == "Now"


def test_current_windows_training_plan_uses_single_process_without_docker_engine(tmp_path: Path) -> None:
    case = next(case for case in load_catalog() if case["case_id"] == "AI-TRN-003")
    options = RunOptions(
        data_dir=tmp_path / "dut",
        results_dir=tmp_path / "results",
        launcher="single",
        mlpstorage=REPO_ROOT / ".venv" / "Scripts" / "mlpstorage.exe",
        dry_run=True,
    )

    plan = build_workload_plan(case, options)

    assert plan["status"] == "READY"
    assert plan["launcher_explanation"] == "single process; no Docker engine is used"
    assert len(plan["commands"]) == 2
    assert all("--exec-type" in command and "docker" in command for command in plan["commands"])
    assert all("docker run" not in " ".join(command).lower() for command in plan["commands"])
    assert all("--dlio-bin-path" in command for command in plan["commands"])
    dlio_path = Path(plan["commands"][0][plan["commands"][0].index("--dlio-bin-path") + 1])
    assert (dlio_path / "dlio_benchmark.exe").is_file()
    assert "reader.multiprocessing_context=spawn" in plan["commands"][1]
    assert plan["commands"][0][1:6] == ["open", "training", "unet3d", "datagen", "file"]


def test_whatif_training_models_and_accelerators_are_not_blocked(tmp_path: Path) -> None:
    by_id = {case["case_id"]: case for case in load_catalog()}
    options = RunOptions(data_dir=tmp_path / "dut", results_dir=tmp_path / "results")

    for case_id, model, accelerator in (
        ("AI-TRN-001", "unet3d", "a100"),
        ("AI-TRN-002", "unet3d", "h100"),
        ("AI-TRN-006", "cosmoflow", "a100"),
        ("AI-TRN-007", "cosmoflow", "h100"),
        ("AI-TRN-008", "resnet50", "a100"),
        ("AI-TRN-009", "resnet50", "h100"),
        ("AI-TRN-010", "dlrm", "b200"),
        ("AI-TRN-011", "dlrm", "mi355"),
        ("AI-TRN-012", "flux", "b200"),
        ("AI-TRN-013", "flux", "mi355"),
    ):
        plan = build_workload_plan(by_id[case_id], options)
        assert plan["status"] == "READY", case_id
        command = plan["commands"][-1]
        assert command[1:4] == ["whatif", "training", model]
        assert command[command.index("--accelerator-type") + 1] == accelerator


def test_extended_kv_models_use_installed_mlperf_kv_cache(tmp_path: Path) -> None:
    by_id = {case["case_id"]: case for case in load_catalog()}
    options = RunOptions(data_dir=tmp_path / "dut", results_dir=tmp_path / "results")

    for case_id, model in (
        ("AI-KV-009", "deepseek-v3"),
        ("AI-KV-010", "qwen3-32b"),
        ("AI-KV-011", "gpt-oss-20b"),
        ("AI-KV-012", "gpt-oss-120b"),
    ):
        plan = build_workload_plan(by_id[case_id], options)
        assert plan["status"] == "READY", case_id
        command = plan["commands"][0]
        assert Path(command[0]).name.lower() in {"mlperf-kv-cache", "mlperf-kv-cache.exe"}
        assert command[command.index("--model") + 1] == model
        assert command[command.index("--config") + 1].endswith("kv_cache_benchmark\\config.yaml")


def test_workflow_cases_offer_explicit_nonformal_try_runs(tmp_path: Path) -> None:
    by_id = {case["case_id"]: case for case in load_catalog()}
    options = RunOptions(
        data_dir=tmp_path / "dut",
        results_dir=tmp_path / "results",
        dry_run=False,
        engineering_smoke=True,
    )

    for case_id in (
        "AI-BASE-002", "AI-BASE-003", "AI-BASE-004",
        "AI-CKP-008", "AI-KV-021", "AI-KV-022", "AI-VDB-015",
        "AI-MIX-001", "AI-MIX-002", "AI-MIX-003", "AI-MIX-004", "AI-MIX-005",
    ):
        plan = build_workload_plan(by_id[case_id], options)
        assert plan["status"] == "READY", case_id
        assert plan["commands"], case_id


def test_cold_restore_and_trace_inputs_map_documented_workflows(tmp_path: Path) -> None:
    by_id = {case["case_id"]: case for case in load_catalog()}
    fixture_root = REPO_ROOT / "full_test_plan_cases" / "fixtures"
    options = RunOptions(
        data_dir=tmp_path / "dut",
        results_dir=tmp_path / "results",
        dry_run=False,
        cache_reset_command="Write-Output cache-reset-approved",
        trace_file=fixture_root / "logical_io_smoke.csv",
        burst_trace=fixture_root / "burstgpt_smoke.csv",
    )

    checkpoint = build_workload_plan(by_id["AI-CKP-008"], options)
    assert checkpoint["status"] == "READY"
    assert len(checkpoint["commands"]) == 3
    assert checkpoint["commands"][0][checkpoint["commands"][0].index("--num-checkpoints-read") + 1] == "0"
    assert checkpoint["commands"][2][checkpoint["commands"][2].index("--num-checkpoints-write") + 1] == "0"

    kv_trace = build_workload_plan(by_id["AI-KV-022"], options)
    assert "--use-burst-trace" in kv_trace["commands"][0]
    assert str(options.burst_trace) in kv_trace["commands"][0]

    vdb_replay = build_workload_plan(by_id["AI-VDB-015"], options)
    assert "vdbbench.replay" in vdb_replay["commands"][0]
    assert str(options.trace_file) in vdb_replay["commands"][0]


def test_formal_training_plan_does_not_bypass_compliance_gates(tmp_path: Path) -> None:
    case = next(case for case in load_catalog() if case["case_id"] == "AI-TRN-003")
    options = RunOptions(
        data_dir=tmp_path / "dut",
        results_dir=tmp_path / "results",
        dry_run=False,
        prepare=False,
    )

    command = build_workload_plan(case, options)["commands"][0]

    assert "--allow-invalid-params" not in command
    assert "--skip-validation" not in command
    assert "--skip-fs-separation-gate" not in command
    assert "--skip-timeseries" not in command
    assert "dataset.num_files_train=8" not in command


def test_engineering_smoke_is_explicitly_nonformal(tmp_path: Path) -> None:
    case = next(case for case in load_catalog() if case["case_id"] == "AI-TRN-003")
    options = RunOptions(
        data_dir=tmp_path / "dut",
        results_dir=tmp_path / "results",
        dry_run=False,
        engineering_smoke=True,
    )

    command = build_workload_plan(case, options)["commands"][0]

    assert "--allow-invalid-params" in command
    assert "--skip-fs-separation-gate" in command
    assert "dataset.num_files_train=8" in command


def test_dry_run_marker_is_not_reported_as_a_passing_workload() -> None:
    assert classify_command_status(6, "Dry-run mode: Command: dlio_benchmark") == "DRY_RUN"
    assert classify_command_status(6, "benchmark failed") == "FAIL"
    assert classify_command_status(0, "complete") == "PASS"


def test_direct_cli_output_parents_are_created(tmp_path: Path) -> None:
    output = tmp_path / "nested" / "result.json"

    prepare_command_output_paths(["mlperf-kv-cache", "--output", str(output)])

    assert output.parent.is_dir()


def test_custom_command_is_preview_only_in_dry_run(tmp_path: Path) -> None:
    case = next(case for case in load_catalog() if case["case_id"] == "AI-MIX-001")
    options = RunOptions(
        data_dir=tmp_path / "dut",
        results_dir=tmp_path / "results",
        dry_run=True,
        custom_command="Write-Output SHOULD_NOT_EXECUTE",
    )

    plan = build_workload_plan(case, options)

    assert plan["status"] == "READY"
    assert plan["commands"] == []
    assert "SHOULD_NOT_EXECUTE" in " ".join(plan["preview_command"])


def test_checkpoint_counts_and_cold_restore_phases_follow_full_plan(tmp_path: Path) -> None:
    by_id = {case["case_id"]: case for case in load_catalog()}
    options = RunOptions(data_dir=tmp_path / "dut", results_dir=tmp_path / "results")

    baseline = build_workload_plan(by_id["AI-CKP-001"], options)
    command = baseline["commands"][0]
    assert command[command.index("--num-checkpoints-write") + 1] == "10"
    assert command[command.index("--num-checkpoints-read") + 1] == "10"

    cold_restore = build_workload_plan(by_id["AI-CKP-008"], options)
    assert cold_restore["status"] == "READY"
    assert len(cold_restore["commands"]) == 2
    assert cold_restore["manual_gate"] is not None


def test_supported_full_matrix_sweeps_are_expanded(tmp_path: Path) -> None:
    by_id = {case["case_id"]: case for case in load_catalog()}
    options = RunOptions(
        data_dir=tmp_path / "dut",
        results_dir=tmp_path / "results",
        matrix=True,
    )

    training = build_workload_plan(by_id["AI-TRN-003"], options)
    accelerator_values = [
        int(command[command.index("--num-accelerators") + 1])
        for command in training["commands"]
        if "--num-accelerators" in command
    ]
    assert accelerator_values == [1, 2, 4, 8]

    kv = build_workload_plan(by_id["AI-KV-007"], options)
    users = [int(command[command.index("--num-users") + 1]) for command in kv["commands"]]
    assert users == [25, 50, 100, 200]

    vdb = build_workload_plan(by_id["AI-VDB-008"], options)
    run_indices = {
        command[command.index("--vdb-index") + 1]
        for command in vdb["commands"]
        if "run" in command
    }
    assert run_indices == {"DISKANN", "HNSW", "AISAQ", "IVF_FLAT", "IVF_SQ8", "FLAT"}


def test_plan_mode_writes_a_manifest_for_every_case(tmp_path: Path) -> None:
    catalog = load_catalog()
    for case in catalog:
        rc = run_case(
            case["case_id"],
            [
                "--mode", "plan",
                "--data-dir", str(tmp_path / "dut"),
                "--results-dir", str(tmp_path / "results"),
            ],
        )
        assert rc == 0, case["case_id"]

    manifests = list((tmp_path / "results").glob("*/manifest.json"))
    assert len(manifests) == 72
    payload = json.loads(
        (tmp_path / "results" / "AI-BASE-001" / "manifest.json").read_text(encoding="utf-8")
    )
    assert payload["case"]["case_id"] == "AI-BASE-001"
    assert payload["mode"] == "plan"
    assert payload["source_sha256"] == SOURCE_SHA256


def test_run_all_is_directly_launchable_from_repo_root() -> None:
    completed = subprocess.run(
        [sys.executable, str(REPO_ROOT / "full_test_plan_cases" / "run_all.py"), "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "Run all matching FULL_TEST_PLAN case entrypoints" in completed.stdout
