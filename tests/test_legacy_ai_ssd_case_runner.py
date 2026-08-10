from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_ssd_test_cases.catalog import CASES, get_case
from ai_ssd_test_cases.runner import build_command, run_case


REPO_ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = REPO_ROOT / "ai_ssd_test_cases"


def test_legacy_catalog_contains_all_72_unique_cases() -> None:
    assert len(CASES) == 72
    assert len(set(CASES)) == 72
    assert get_case("AI-TRN-001").family == "Training"
    assert get_case("AI-MIX-005").family == "Mixed"
    assert get_case("AI-TRN-004").entrypoint.endswith("test_ai_trn_004_retinanet_b200_jpeg.py")
    assert get_case("AI-KV-001").entrypoint.endswith("test_kv_option1_8b_nvme_only.py")
    assert get_case("AI-VDB-003").entrypoint.endswith("test_vdb_diskann_1m_1536.py")


def test_legacy_entrypoints_exist_for_every_case() -> None:
    missing = [spec.entrypoint for spec in CASES.values() if not (REPO_ROOT / spec.entrypoint).is_file()]
    assert missing == []


def test_legacy_entrypoint_filenames_include_case_design() -> None:
    for spec in CASES.values():
        filename = Path(spec.entrypoint).stem
        generic_name = f"test_{spec.case_id.lower().replace('-', '_')}"
        assert filename.startswith("test_")
        assert filename != generic_name
        assert len(filename.split("_")) >= 4


def test_build_command_uses_current_native_entrypoint_for_supported_case(tmp_path: Path) -> None:
    command = build_command(
        "AI-TRN-003",
        data_dir=tmp_path / "data",
        results_dir=tmp_path / "results",
        prepare=False,
    )

    assert command[0].endswith("python.exe") or command[0].endswith("python")
    assert command[1].endswith("full_test_plan_cases\\cases\\test_ai_trn_003.py")
    assert "--confirm-dut" in command


def test_run_case_requires_execute_and_writes_blocked_manifest(tmp_path: Path) -> None:
    result = run_case(
        "AI-TRN-006",
        [
            "--execute",
            "--data-dir",
            str(tmp_path / "data"),
            "--result-dir",
            str(tmp_path / "results"),
        ],
    )

    assert result == 2
    manifests = list((tmp_path / "results" / "AI-TRN-006").glob("*/manifest.json"))
    assert len(manifests) == 1
    payload = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert payload["status"] == "BLOCKED"
    assert "native" in payload["reason"].lower()


@pytest.mark.parametrize("case_id", ["AI-BASE-001", "AI-BASE-002", "AI-BASE-003"])
def test_python_base_cases_can_run_scaled(tmp_path: Path, case_id: str) -> None:
    result = run_case(
        case_id,
        [
            "--execute",
            "--data-dir",
            str(tmp_path / "data"),
            "--result-dir",
            str(tmp_path / "results"),
            "--scale-mb",
            "8",
        ],
    )

    assert result == 0
    verdicts = list((tmp_path / "results" / case_id).glob("*/verdict.json"))
    assert len(verdicts) == 1
    assert json.loads(verdicts[0].read_text(encoding="utf-8"))["status"] == "PASS"
