"""Unit tests for ``ai_ssd_test_cases.training._common``.

These tests pin the contract that the 16 Training case wrappers rely on:

* every case has a registered ``CaseInfo`` in ``DEFAULT_CASES``;
* native / native_special cases build a command without ``--scale-mb``;
* python_scaled cases build a command with ``--scale-mb``;
* layout guard rejects ``--result-dir`` inside ``--data-dir``;
* argparse surface accepts the standard flag set without error;
* the 16 wrapper files in the directory each have a parseable module
  that imports ``DEFAULT_CASES`` and ``main`` from ``_common``.

The tests do not invoke the inner runner; the end-to-end smoke run
lives in ``scripts/run_16_training_smoke.py``.
"""

from __future__ import annotations

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from ai_ssd_test_cases.training._common import (  # noqa: E402
    DEFAULT_CASES,
    build_argparser,
    build_command,
)


def test_all_sixteen_training_cases_registered() -> None:
    expected = {f"AI-TRN-{number:03d}" for number in range(1, 17)}
    assert set(DEFAULT_CASES) == expected


def test_native_cases_have_no_python_scaled_execution() -> None:
    for case_id in ("AI-TRN-001", "AI-TRN-003", "AI-TRN-004", "AI-TRN-005"):
        info = DEFAULT_CASES[case_id]
        assert info.execution in {"native", "native_special"}, case_id


def test_python_scaled_cases_match_catalog() -> None:
    expected_scaled = {
        "AI-TRN-002", "AI-TRN-006", "AI-TRN-007", "AI-TRN-008", "AI-TRN-009",
        "AI-TRN-010", "AI-TRN-011", "AI-TRN-012", "AI-TRN-013",
        "AI-TRN-014", "AI-TRN-015", "AI-TRN-016",
    }
    actual = {c for c, info in DEFAULT_CASES.items() if info.execution == "python_scaled"}
    assert actual == expected_scaled


def test_training_cases_are_not_destructive() -> None:
    # Per ai_ssd_test_cases/catalog the Training family is non-destructive;
    # destructive flags are reserved for BASE-004 / Checkpoint / Mixed.
    for info in DEFAULT_CASES.values():
        assert info.destructive is False, info.case_id


def test_dataset_size_does_not_equal_target_ssd() -> None:
    # Each CaseInfo records the *dataset* size, not the target SSD tier
    # (1 TB / 2 TB / 4 TB column in the xlsx).  The two should not
    # accidentally be conflated.
    for info in DEFAULT_CASES.values():
        assert info.capacity_gib < 1000, (
            f"{info.case_id}: capacity_gib={info.capacity_gib} looks like a target SSD"
        )


def _build_args(**overrides):
    defaults = dict(
        data_dir=Path("D:/d"),
        result_dir=Path("E:/r"),
        duration_sec=300,
        repeat=3,
        scale_mb=1024,
        prepare=False,
        confirm_dut=False,
        keep_data=False,
        timeout_sec=90.0,
        dry_run=False,
    )
    defaults.update(overrides)
    return Namespace(**defaults)


def test_build_command_includes_execute_and_required_flags() -> None:
    args = _build_args(prepare=True, confirm_dut=True, duration_sec=300, repeat=3, scale_mb=None)
    cmd = build_command("AI-TRN-003", args, REPO_ROOT / ".venv" / "Scripts" / "python.exe")
    assert "--case" in cmd and "AI-TRN-003" in cmd
    assert "--execute" in cmd
    assert "--prepare" in cmd
    assert "--confirm-dut" in cmd
    assert "--scale-mb" not in cmd  # native case does not pass --scale-mb
    assert "--data-dir" in cmd
    assert "--result-dir" in cmd


def test_build_command_python_scaled_path() -> None:
    args = _build_args(duration_sec=60, repeat=1, scale_mb=2048)
    cmd = build_command("AI-TRN-006", args, REPO_ROOT / ".venv" / "Scripts" / "python.exe")
    assert "--scale-mb" in cmd and "2048" in cmd
    assert "--prepare" not in cmd
    assert "--confirm-dut" not in cmd


def test_argparse_accepts_standard_flags() -> None:
    parser = build_argparser("AI-TRN-001")
    parsed = parser.parse_args([
        "--data-dir", "D:/d",
        "--result-dir", "E:/r",
        "--scale-mb", "512",
        "--duration-sec", "60",
        "--repeat", "2",
        "--timeout-sec", "30",
        "--dry-run",
    ])
    assert parsed.data_dir == Path("D:/d")
    assert parsed.result_dir == Path("E:/r")
    assert parsed.scale_mb == 512
    assert parsed.dry_run is True


def test_layout_guard_rejects_result_inside_data(tmp_path: Path) -> None:
    from ai_ssd_test_cases.training._common import _validate_layout
    data = tmp_path / "data"
    data.mkdir()
    nested = data / "results"
    nested.mkdir()
    issues = _validate_layout(data, nested)
    assert any("result-dir must not be inside" in issue for issue in issues)


def test_sixteen_wrapper_files_exist_and_import() -> None:
    training_dir = REPO_ROOT / "ai_ssd_test_cases" / "training"
    wrappers = sorted(training_dir.glob("test_training_*.py"))
    assert len(wrappers) == 16, f"expected 16 wrappers, found {len(wrappers)}"

    for path in wrappers:
        spec = importlib.util.spec_from_file_location(path.stem, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "DEFAULT_CASES"), f"{path.name} missing DEFAULT_CASES import"
        assert hasattr(mod, "main"), f"{path.name} missing main import"
        # every wrapper references one entry in DEFAULT_CASES; the
        # case_id is encoded in the filename as ``ai_trn_<NNN>``.
        nnn = next(
            (p for p in path.stem.split("_") if p.isdigit() and len(p) == 3),
            None,
        )
        assert nnn is not None, f"{path.name} does not contain a TRN number"
        case_id = f"AI-TRN-{nnn}"
        assert case_id in mod.DEFAULT_CASES, f"{path.name} does not match any DEFAULT_CASES id"
